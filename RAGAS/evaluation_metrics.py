import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import Counter
import re
from typing import List, Dict, Any
from difflib import SequenceMatcher, get_close_matches

# === Local Metrics Implementation ===
class LocalRAGMetrics:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    
    def context_relevance(self, query: str, contexts: List[str]) -> float:
        """Calculate how relevant the retrieved contexts are to the query"""
        if not contexts or not query.strip():
            return 0.0
        
        # Combine all contexts
        all_contexts = " ".join(contexts)
        
        # Vectorize query and contexts
        texts = [query, all_contexts]
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0
    
    def context_precision(self, query: str, contexts: List[str], response: str) -> float:
        """Calculate precision of retrieved contexts based on response usage"""
        if not contexts or not response.strip():
            return 0.0
        
        # Simple heuristic: check how many contexts have overlapping keywords with response
        response_words = set(re.findall(r'\b\w+\b', response.lower()))
        relevant_contexts = 0
        
        for context in contexts:
            context_words = set(re.findall(r'\b\w+\b', context.lower()))
            # If context shares significant words with response, consider it relevant
            overlap = len(response_words.intersection(context_words))
            if overlap > 2:  # threshold for relevance
                relevant_contexts += 1
        
        return relevant_contexts / len(contexts) if contexts else 0.0
    
    def context_recall(self, ground_truth: str, contexts: List[str]) -> float:
        """Calculate how well contexts cover the ground truth information"""
        if not contexts or not ground_truth.strip():
            return 0.0
        
        # Vectorize ground truth and contexts
        all_contexts = " ".join(contexts)
        texts = [ground_truth, all_contexts]
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0
    
    def answer_relevance(self, query: str, response: str) -> float:
        """Calculate how relevant the response is to the query"""
        if not query.strip() or not response.strip():
            return 0.0
        
        texts = [query, response]
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0
    
    def answer_correctness(self, ground_truth: str, response: str) -> float:
        """Calculate how correct the response is compared to ground truth"""
        if not ground_truth.strip() or not response.strip():
            return 0.0
        
        texts = [ground_truth, response]
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0
    
    def evaluate_all(self, query: str, ground_truth: str, response: str, contexts: List[str]) -> Dict[str, float]:
        """Evaluate all metrics and return a dictionary of scores"""
        return {
            "context_relevance": self.context_relevance(query, contexts),
            "context_precision": self.context_precision(query, contexts, response),
            "context_recall": self.context_recall(ground_truth, contexts),
            "answer_relevance": self.answer_relevance(query, response),
            "answer_correctness": self.answer_correctness(ground_truth, response)
        }

# === Load environment variables ===
load_dotenv()
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "ragas")
OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL", "http://localhost:11446")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# === Helper Functions ===
def normalize_query(query):
    """Normalize query for better matching"""
    # Convert to lowercase, strip whitespace, remove extra spaces, remove special chars
    normalized = re.sub(r'[^\w\s]', '', query.lower().strip())
    normalized = re.sub(r'\s+', ' ', normalized)  # Replace multiple spaces with single space
    return normalized

# === Load JSON Dataset with Enhanced Key Matching ===
try:
    with open("final_dataset1.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    # Create multiple mappings for better matching
    hf_dict = {}
    hf_dict_normalized = {}
    hf_dict_original = {}
    
    for row in raw_data:
        original_query = row['query']
        ground_truth = row['ground_truth']
        
        # Store with different normalizations
        hf_dict[original_query.strip().lower()] = ground_truth
        hf_dict_normalized[normalize_query(original_query)] = ground_truth
        hf_dict_original[original_query] = ground_truth
    
    print(f"✅ Loaded {len(raw_data)} queries from dataset")
    print(f"📋 Sample queries from dataset:")
    for i, query in enumerate(list(hf_dict.keys())[:3]):
        print(f"  [{i+1}] '{query}'")
    
except FileNotFoundError:
    print("⚠️ final_dataset1.json not found. Creating empty dataset.")
    hf_dict = {}
    hf_dict_normalized = {}
    hf_dict_original = {}

# === Qdrant Setup (Mock if not available) ===
class MockQdrantManager:
    def __init__(self, collection_name):
        self.collection_name = collection_name
        print(f"🔧 Mock Qdrant Manager initialized for collection: {collection_name}")
    
    def search(self, query, limit=3):
        # Return mock contexts for testing
        return [
            {"text": f"Mock context 1 for query: {query[:50]}..."},
            {"text": f"Mock context 2 related to: {query[:50]}..."},
            {"text": f"Mock context 3 discussing: {query[:50]}..."}
        ]

try:
    from qdrant import QdrantManager
    qdrant = QdrantManager(collection_name=QDRANT_COLLECTION)
    print("✅ Qdrant Manager initialized")
except ImportError:
    print("⚠️ Qdrant not available, using mock manager")
    qdrant = MockQdrantManager(collection_name=QDRANT_COLLECTION)

# === Initialize Local Metrics ===
metrics_calculator = LocalRAGMetrics()

# === Core Functions ===
def find_ground_truth(query):
    """Enhanced ground truth finder with multiple matching strategies"""
    # Strategy 1: Direct lowercase match
    gt = hf_dict.get(query.strip().lower())
    if gt:
        return gt, "direct_match"
    
    # Strategy 2: Normalized match (remove punctuation, extra spaces)
    normalized_query = normalize_query(query)
    gt = hf_dict_normalized.get(normalized_query)
    if gt:
        return gt, "normalized_match"
    
    # Strategy 3: Fuzzy matching using similarity
    best_match = None
    best_score = 0
    match_type = "fuzzy_match"
    
    # Check similarity with all keys
    for key in hf_dict.keys():
        similarity = SequenceMatcher(None, query.lower().strip(), key).ratio()
        if similarity > best_score and similarity > 0.8:  # 80% similarity threshold
            best_score = similarity
            best_match = hf_dict[key]
    
    if best_match:
        return best_match, f"fuzzy_match (similarity: {best_score:.2f})"
    
    # Strategy 4: Contains match (check if any dataset query contains the input or vice versa)
    query_lower = query.lower().strip()
    for key, value in hf_dict.items():
        if query_lower in key or key in query_lower:
            return value, "contains_match"
    
    return None, "no_match"

def get_context(query, top_k=3):
    """Retrieve contexts for a query"""
    try:
        results = qdrant.search(query, limit=top_k)
        return [r["text"] for r in results] if results else [""]
    except Exception as e:
        print(f"⚠️ Context retrieval error: {e}")
        return [f"Fallback context for: {query}"]

def get_ollama_response(query, context):
    """Get response from Ollama API"""
    prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nPlease provide a helpful answer based on the context provided."
    
    try:
        response = requests.post(
            f"{OLLAMA_SERVER_URL}/api/chat",
            headers={"Content-Type": "application/json"},
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant. Answer questions based only on the provided context. If the context doesn't contain relevant information, say so clearly."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            response_json = response.json()
            return response_json["message"]["content"].strip()
        else:
            return f"Error: HTTP {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama API Error: {e}")
        return f"Error: Failed to connect to Ollama server. Please check if Ollama is running at {OLLAMA_SERVER_URL}"
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return "Error: Failed to get valid response from Ollama."

def evaluate_single(query, ground_truth, response, contexts):
    """Evaluate a single query-response pair using local metrics"""
    scores = metrics_calculator.evaluate_all(query, ground_truth, response, contexts)
    
    # Create a DataFrame for consistent output format
    df = pd.DataFrame([{
        "query": query,
        **scores
    }])
    
    return df

def plot_metrics(df):
    """Plot evaluation metrics"""
    if df.empty:
        print("⚠️ No data to plot.")
        return
    
    # Extract metrics (excluding query column)
    metrics = df.drop("query", axis=1).iloc[0]
    metrics = metrics.dropna()
    
    if len(metrics) == 0:
        print("⚠️ No valid metrics to plot.")
        return
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    bars = plt.bar(metrics.index, metrics.values, color=['skyblue', 'lightcoral', 'lightgreen', 'orange', 'plum'])
    
    # Customize the plot
    plt.ylim(0, 1.1)
    plt.title("Local RAG Evaluation Metrics", fontsize=16, fontweight='bold')
    plt.ylabel("Score", fontsize=12)
    plt.xlabel("Metrics", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig("local_rag_metrics.png", dpi=300, bbox_inches='tight')
    plt.show()

def save_detailed_results(query, ground_truth, response, contexts, scores, filename="detailed_results.json"):
    """Save detailed evaluation results"""
    result = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "query": query,
        "ground_truth": ground_truth,
        "response": response,
        "contexts": contexts,
        "scores": scores,
        "summary": {
            "avg_score": np.mean(list(scores.values())),
            "best_metric": max(scores, key=scores.get),
            "worst_metric": min(scores, key=scores.get)
        }
    }
    
    # Load existing results or create new
    try:
        with open(filename, "r", encoding="utf-8") as f:
            results = json.load(f)
    except FileNotFoundError:
        results = []
    
    results.append(result)
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    return result

# === Main Interactive Loop ===
response_log = []
print("\n🎯 Local RAG Evaluation System (No API Dependencies)")
print("=" * 60)
print("📊 Available Metrics:")
print("  • Context Relevance: How relevant contexts are to the query")
print("  • Context Precision: How precisely contexts relate to the response")
print("  • Context Recall: How well contexts cover ground truth")
print("  • Answer Relevance: How relevant the response is to the query")
print("  • Answer Correctness: How correct the response is vs ground truth")
print("=" * 60)
print("Type 'exit' to quit, 'stats' to see overall statistics\n")

while True:
    query = input("🔍 Enter a user query: ").strip()
    
    if query.lower() == "exit":
        break
    elif query.lower() == "stats":
        if response_log:
            print(f"\n📈 Session Statistics:")
            print(f"  • Total queries processed: {len(response_log)}")
            print(f"  • Queries with ground truth: {sum(1 for r in response_log if r['ground_truth'] is not None)}")
            print(f"  • Average response length: {np.mean([len(r['llm_response']) for r in response_log]):.1f} characters")
        else:
            print("📊 No queries processed yet.")
        continue
    
    if not query:
        print("⚠️ Please enter a valid query.")
        continue
    
    print(f"\n🔄 Processing query: '{query}'")
    
    # Get contexts
    contexts = get_context(query)
    context_str = " ".join(contexts)
    
    # Get response
    response = get_ollama_response(query, context_str)
    
    # Display results
    print("\n📚 Retrieved Contexts:")
    for i, ctx in enumerate(contexts, 1):
        print(f"  [{i}] {ctx[:200]}{'...' if len(ctx) > 200 else ''}")
    
    print(f"\n🤖 Ollama Response:\n{response}\n")
    
    # Check for ground truth and evaluate with enhanced matching
    gt, match_type = find_ground_truth(query)
    if gt:
        print(f"🎯 Ground Truth Found ({match_type}) → Running Local Evaluation...")
        print(f"📋 Ground Truth: {gt}\n")
        
        # Evaluate using local metrics
        df = evaluate_single(query, gt, response, contexts)
        scores = df.drop("query", axis=1).iloc[0].to_dict()
        
        # Display results
        print("📊 Evaluation Results:")
        print(df.to_string(index=False, float_format='%.3f'))
        
        # Plot metrics
        plot_metrics(df)
        
        # Save detailed results
        detailed_result = save_detailed_results(query, gt, response, contexts, scores)
        
        response_log.append({
            "query": query,
            "ground_truth": gt,
            "llm_response": response,
            "contexts": contexts,
            "scores": scores
        })
        
        print(f"\n✨ Summary: Avg Score = {detailed_result['summary']['avg_score']:.3f}")
        print(f"   Best: {detailed_result['summary']['best_metric']} | Worst: {detailed_result['summary']['worst_metric']}")
        
    else:
        print("⚠️ Ground truth not found in dataset — running partial evaluation...")
        print(f"🔍 Tried matching strategies: direct, normalized, fuzzy, contains")
        
        # Debug: Show similar queries for troubleshooting
        print("\n🔍 Most similar queries in dataset:")
        similar = get_close_matches(query.lower().strip(), list(hf_dict.keys()), n=3, cutoff=0.3)
        for i, sim_query in enumerate(similar, 1):
            print(f"  [{i}] '{sim_query}'")
        
        # Still calculate metrics that don't require ground truth
        partial_scores = {
            "context_relevance": metrics_calculator.context_relevance(query, contexts),
            "answer_relevance": metrics_calculator.answer_relevance(query, response)
        }
        
        print(f"\n📊 Partial Evaluation (no ground truth):")
        for metric, score in partial_scores.items():
            print(f"  • {metric}: {score:.3f}")
        
        response_log.append({
            "query": query,
            "ground_truth": None,
            "llm_response": response,
            "contexts": contexts,
            "scores": partial_scores
        })
    
    # Save response log
    with open("live_response_log.json", "w", encoding="utf-8") as f:
        json.dump(response_log, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Results saved to live_response_log.json and detailed_results.json")
    print("=" * 60 + "\n")

print("\n👋 Session ended. Check the generated files for detailed results!")