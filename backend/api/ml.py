from flask import Blueprint, request
from typing import Dict, Any, List
import numpy as np
from collections import defaultdict
from backend.api.responses import success_response, error_response
from backend.database.session import SessionLocal
from backend.services.budget import budget_service
from backend.models.budget import BudgetStage
from backend.ml.budget_clustering import BudgetKMeansClustering
from backend.ml.budget_dbscan import BudgetDBSCANClustering
from backend.ml.budget_pca import BudgetPCAAnalysis
from backend.ml.budget_anomaly import BudgetIsolationForest

ml_bp = Blueprint('ml', __name__, url_prefix='/ml')

def _build_source_map(records) -> Dict[tuple, List[str]]:
    """Maps (dept, scheme, year) to a list of source document IDs."""
    source_map = defaultdict(set)
    for r in records:
        if r.scheme and r.scheme.department:
            key = (r.scheme.department.name, r.scheme.name, r.financial_year)
            if r.source_document_id:
                source_map[key].add(str(r.source_document_id))
    return {k: list(v) for k, v in source_map.items()}

def _apply_source_map(df, source_map):
    """Applies source map to the dataframe."""
    def get_sources(row):
        key = (row["department"], row["scheme"], row["financial_year"])
        return source_map.get(key, [])
    df["source_documents"] = df.apply(get_sources, axis=1)
    return df


@ml_bp.route('/budget/clustering', methods=['GET'])
def get_budget_clustering():
    """
    Returns chart-ready clustering output alongside a 2D PCA projection 
    for visualization and feature exploration.
    """
    algorithm = request.args.get('algorithm', 'kmeans')
    stage_str = request.args.get('budget_stage')
    dept_id = request.args.get('department_id', type=int)
    scheme_id = request.args.get('scheme_id', type=int)
    fin_year = request.args.get('financial_year')
    
    if not stage_str:
        return error_response("budget_stage is required.", status_code=400)
        
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response("Invalid budget_stage.", status_code=400)
        
    db = SessionLocal()
    try:
        # Fetch raw records
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=50000, 
            budget_stage=stage, 
            department_id=dept_id,
            scheme_id=scheme_id,
            financial_year=fin_year
        )
        
        if len(records) < 2:
            return error_response("Insufficient records for ML clustering (minimum 2).", status_code=400)
            
        source_map = _build_source_map(records)
            
        # 1. Run the chosen clustering algorithm
        cluster_df = None
        summaries = {}
        if algorithm == 'kmeans':
            k = request.args.get('k', 3, type=int)
            model = BudgetKMeansClustering()
            cluster_df = model.fit_predict(records, k=k)
            summaries = model.get_cluster_summaries(cluster_df)
        elif algorithm == 'dbscan':
            eps = request.args.get('eps', 0.5, type=float)
            min_samples = request.args.get('min_samples', 3, type=int)
            model = BudgetDBSCANClustering(eps=eps, min_samples=min_samples)
            cluster_df = model.fit_predict(records)
            summaries = model.get_cluster_summaries(cluster_df)
        else:
            return error_response(f"Unsupported algorithm: {algorithm}", status_code=400)
            
        # 2. Run PCA (2 components) on the EXACT same records
        pca = BudgetPCAAnalysis(n_components=2)
        pca_df = pca.fit_transform(records)
        variance_stats = pca.get_explained_variance()
        
        # 3. Merge PCA dimensions into cluster assignments based on identifiers
        merged_df = cluster_df.merge(
            pca_df[["department", "scheme", "financial_year", "PC1", "PC2"]], 
            on=["department", "scheme", "financial_year"],
            how="inner"
        )
        
        # Apply sources
        merged_df = _apply_source_map(merged_df, source_map)
        
        # 4. Prepare chart-ready JSON structure
        # Convert numeric NaNs to None for valid JSON serialization
        merged_df = merged_df.replace({np.nan: None})
        
        output_data = {
            "algorithm": algorithm,
            "explained_variance": variance_stats,
            "summaries": summaries,
            "data_points": merged_df.to_dict(orient="records")
        }
        
        return success_response(data=output_data)
        
    except ValueError as e:
        return error_response(str(e), status_code=400)
    except Exception as e:
        return error_response(f"Clustering error: {str(e)}", status_code=500)
    finally:
        db.close()


@ml_bp.route('/budget/anomaly', methods=['GET'])
def get_budget_anomaly():
    """
    Returns Isolation Forest anomaly scores and flags for budget records.
    """
    stage_str = request.args.get('budget_stage')
    dept_id = request.args.get('department_id', type=int)
    scheme_id = request.args.get('scheme_id', type=int)
    fin_year = request.args.get('financial_year')
    contamination = request.args.get('contamination', 'auto')
    
    if not stage_str:
        return error_response("budget_stage is required.", status_code=400)
        
    try:
        stage = BudgetStage(stage_str)
    except ValueError:
        return error_response("Invalid budget_stage.", status_code=400)
        
    if contamination != 'auto':
        try:
            contamination = float(contamination)
        except ValueError:
            return error_response("contamination must be 'auto' or a float.", status_code=400)
            
    db = SessionLocal()
    try:
        records, _ = budget_service.get_filtered_records(
            db, skip=0, limit=50000, 
            budget_stage=stage, 
            department_id=dept_id,
            scheme_id=scheme_id,
            financial_year=fin_year
        )
        
        if len(records) < 2:
            return error_response("Insufficient records for Anomaly Detection (minimum 2).", status_code=400)
            
        source_map = _build_source_map(records)
            
        model = BudgetIsolationForest(contamination=contamination)
        anomaly_df = model.fit_predict(records)
        
        anomaly_df = _apply_source_map(anomaly_df, source_map)
        
        # Get purely the flagged records as a quick summary
        flagged_records = model.get_flagged_records(anomaly_df)
        
        anomaly_df = anomaly_df.replace({np.nan: None})
        
        output_data = {
            "algorithm": "isolation_forest",
            "metadata": {
                "contamination": contamination,
                "total_analyzed": len(anomaly_df),
                "total_anomalies": len(flagged_records)
            },
            "flagged_summary": flagged_records,
            "data_points": anomaly_df.to_dict(orient="records")
        }
        
        return success_response(data=output_data)
        
    except ValueError as e:
        return error_response(str(e), status_code=400)
    except Exception as e:
        return error_response(f"Anomaly detection error: {str(e)}", status_code=500)
    finally:
        db.close()
