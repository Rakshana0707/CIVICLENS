import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session
import logging

from backend.models.budget import HistoricalScheme, SchemeCategory
from backend.nlp.scheme_preprocessing import SchemeTextPreprocessor

logger = logging.getLogger(__name__)

class ThemeAnalyzer:
    """
    Unsupervised theme analysis for historical schemes using Sentence Embeddings + KMeans,
    combined with TF-IDF for interpretable keyword extraction.
    """
    def __init__(self, db_session: Session):
        self.db = db_session
        self.preprocessor = SchemeTextPreprocessor()

    def extract_keywords_tfidf(self, texts: List[str], top_n: int = 5) -> List[str]:
        """Extracts top keywords using TF-IDF for a cluster of texts."""
        if not texts:
            return []
            
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        try:
            X = vectorizer.fit_transform(texts)
            indices = np.argsort(vectorizer.idf_)[::-1]
            features = vectorizer.get_feature_names_out()
            
            # Simple TF-IDF sum across the cluster
            scores = np.sum(X.toarray(), axis=0)
            top_indices = np.argsort(scores)[::-1][:top_n]
            return [features[i] for i in top_indices]
        except ValueError:
            return []

    def analyze_themes(self, n_clusters: int = 5, department_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Groups schemes into clusters based on their pre-calculated semantic embeddings.
        Generates interpretable labels using TF-IDF.
        """
        query = self.db.query(HistoricalScheme)
        if department_id:
            query = query.filter(HistoricalScheme.department_id == department_id)
            
        schemes = query.all()
        
        valid_schemes = []
        vectors = []
        texts = []
        
        # 1. Gather pre-computed embeddings and texts
        for s in schemes:
            if s.embedding and isinstance(s.embedding, dict) and "vector" in s.embedding:
                raw_dict = {
                    "scheme_name": s.scheme_name,
                    "description": s.description,
                    "objectives": s.objectives
                }
                text = self.preprocessor.generate_semantic_text(raw_dict)
                
                valid_schemes.append(s)
                vectors.append(s.embedding["vector"])
                texts.append(text)
                
        if len(valid_schemes) < n_clusters:
            raise ValueError("Not enough schemes with embeddings to form requested clusters.")
            
        # 2. Cluster using KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(vectors)
        
        # 3. Organize into themes
        themes = []
        for cluster_id in range(n_clusters):
            cluster_indices = [i for i, label in enumerate(labels) if label == cluster_id]
            cluster_schemes = [valid_schemes[i] for i in cluster_indices]
            cluster_texts = [texts[i] for i in cluster_indices]
            
            # Generate keywords
            keywords = self.extract_keywords_tfidf(cluster_texts, top_n=5)
            
            # Map existing categories
            categories = {}
            for s in cluster_schemes:
                cat_name = s.category.name if s.category else "Uncategorized"
                categories[cat_name] = categories.get(cat_name, 0) + 1
            
            # Formatting representatives
            representatives = []
            for s in cluster_schemes[:5]: # top 5 reps
                representatives.append({
                    "id": s.id,
                    "scheme_name": s.scheme_name,
                    "financial_year": s.financial_year,
                    "department": s.department.name if s.department else "Unknown"
                })
                
            themes.append({
                "theme_id": cluster_id,
                "theme_name": f"Theme {cluster_id + 1}: {', '.join(keywords).title()}",
                "keywords": keywords,
                "scheme_count": len(cluster_schemes),
                "documented_categories": categories,
                "representative_schemes": representatives,
                "disclaimer": "Themes are generated statistically via unsupervised learning and carry no implied political intent."
            })
            
        return {
            "n_clusters": n_clusters,
            "total_schemes_analyzed": len(valid_schemes),
            "themes": themes
        }
