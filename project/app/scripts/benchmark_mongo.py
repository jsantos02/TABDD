import time
from app.db.mongo import mongo_db

def run_benchmark():
    col = mongo_db["vehicles"]
    line_query = "LINE_M_A"
    iterations = 5000  # Mongo reads are very fast, so we need more loops

    print(f"--- MONGODB BENCHMARK ({iterations} iterations) ---")

    # 1. Ensure Index Exists (Setup)
    col.create_index("line")
    
    # 2. Measure WITH Index
    start = time.time()
    for _ in range(iterations):
        # Convert cursor to list to force actual fetch
        _ = list(col.find({"line": line_query}))
    end = time.time()
    time_index = end - start
    print(f"WITH Index:    {time_index:.4f} seconds")

    # 3. Drop Index to simulate "Before Optimization"
    try:
        col.drop_index("line_1") # Default mongo name for {line: 1} is line_1
    except Exception as e:
        print(f"Warning: Could not drop index (might not exist): {e}")

    # 4. Measure WITHOUT Index
    start = time.time()
    for _ in range(iterations):
        _ = list(col.find({"line": line_query}))
    end = time.time()
    time_no_index = end - start
    print(f"WITHOUT Index: {time_no_index:.4f} seconds")

    # 5. Restore Index (Cleanup)
    col.create_index("line")
    print("Index restored.")

    # Conclusion
    if time_no_index > 0:
        improvement = (time_no_index - time_index) / time_no_index * 100
        print(f"Improvement:   {improvement:.1f}% faster with index")

if __name__ == "__main__":
    run_benchmark()