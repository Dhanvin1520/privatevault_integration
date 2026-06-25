import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss


def _load_regulation_documents():
    """
    Scans the data/regulations directory and builds a corpus of financial 
    guidelines indexed for vector retrieval.
    
    Returns:
        list: A list of dictionaries containing 'text' and 'source' for every chunk.
    """
    docs = []
    reg_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'regulations')
    for filename in sorted(os.listdir(reg_dir)):
        if filename.endswith('.txt'):
            filepath = os.path.join(reg_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            source_name = filename.replace('.txt', '').replace('_', ' ').title()
            chunks = _chunk_text(content, chunk_size=300, overlap=50)
            for chunk in chunks:
                docs.append({'text': chunk, 'source': source_name})
    return docs


def _chunk_text(text, chunk_size=300, overlap=50):
    """
    Performs sliding-window chunking on long regulation text to maintain 
    semantic context and handle LLM context limits.
    
    Args:
        text (str): Raw text content.
        chunk_size (int): Max words per chunk.
        overlap (int): Word overlap between consecutive chunks.
        
    Returns:
        list: List of text chunks.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


class RegulationRetriever:
    """
    A FAISS-backed retrieval system that uses TF-IDF vectorization to provide 
    semantically relevant banking regulations (RBI/Basel III) for a given query.
    """
    def __init__(self):
        """
        Initializes the TF-IDF vectorizer and builds the flat Inner Product 
        (IP) FAISS index for high-speed similarity search.
        """
        self.documents = _load_regulation_documents()
        texts = [doc['text'] for doc in self.documents]
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        tfidf_matrix = self.vectorizer.fit_transform(texts).toarray().astype(np.float32)
        
        # L2-Norm the vectors to allow Inner Product (IP) to serve as Cosine Similarity
        norms = np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        tfidf_matrix = tfidf_matrix / norms
        
        dimension = tfidf_matrix.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(tfidf_matrix)

    def retrieve(self, query: str, k: int = 5) -> list:
        """
        Finds the top-k most relevant regulation chunks for a borrower profile.
        
        Args:
            query (str): The search query (usually a borrower summary).
            k (int): Number of sources to retrieve.
            
        Returns:
            list: Ranked results containing text, source, and similarity score.
        """
        query_vec = self.vectorizer.transform([query]).toarray().astype(np.float32)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm
        scores, indices = self.index.search(query_vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({
                    'text': self.documents[idx]['text'],
                    'source': self.documents[idx]['source'],
                    'score': float(score)
                })
        return results
