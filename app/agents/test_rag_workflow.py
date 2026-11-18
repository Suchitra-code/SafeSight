
from rag_workflow import run_workflow

result = run_workflow(
    query="Does the worker have a helmet?",
    visual_events=["Worker detected. Helmet not detected."],
    document_chunks=[
        "Workers must wear safety helmets in construction areas."
    ]
)

print("\nFINAL ANSWER:\n")
print(result["answer"])
print("\nVALIDATION:", result["valid"])
