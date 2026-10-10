import time

from sara.model import OllamaModelClient
from sara.batch_screening import screen_papers_in_batches
from sara.prompts import SEMANTIC_SCREENING_PROMPT
from sara.schemas import (
    validate_semantic_screening,
    parse_semantic_screening,
)

QUESTION = (
    "How is deep learning used for leukemia detection "
    "in peripheral blood smear images?"
)

PAPERS = [
    {
        "id": "P1",
        "title": "CNN-Based Leukemia Detection",
        "abstract": (
            "This study applies convolutional neural networks "
            "to detect leukemia in peripheral blood smear images."
        ),
    },
    {
        "id": "P2",
        "title": "Deep Learning Classification of Blood Cells",
        "abstract": (
            "A deep learning model classifies leukemic and healthy "
            "cells using microscopic peripheral blood images."
        ),
    },
    {
        "id": "P3",
        "title": "LSTM and CNN for Leukemia Recognition",
        "abstract": (
            "A hybrid CNN-LSTM architecture identifies leukemia "
            "from peripheral blood smear images."
        ),
    },
    {
        "id": "P4",
        "title": "Machine Learning for Traffic Forecasting",
        "abstract": (
            "This paper predicts road traffic congestion using "
            "machine learning and transportation sensor data."
        ),
    },
    {
        "id": "P5",
        "title": "Deep Learning for Plant Disease Detection",
        "abstract": (
            "Convolutional neural networks detect plant diseases "
            "from agricultural leaf images."
        ),
    },
]


class CountingModel:
    def __init__(self):
        self.client = OllamaModelClient()
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return self.client.generate(prompt)


print("=== BATCH SCREENING ===")

batch_model = CountingModel()
start = time.perf_counter()

batch_results = screen_papers_in_batches(
    papers=PAPERS,
    research_question=QUESTION,
    model_client=batch_model,
    batch_size=5,
)

batch_time = time.perf_counter() - start

for result in batch_results:
    print(
        result["paper"]["id"],
        result["decision"],
        result["status"],
    )

print("Batch calls:", batch_model.calls)
print(f"Batch time: {batch_time:.2f} seconds")


print("\n=== INDIVIDUAL SCREENING ===")

individual_model = CountingModel()
start = time.perf_counter()

individual_results = []

for paper in PAPERS:
    prompt = SEMANTIC_SCREENING_PROMPT.format(
        research_question=QUESTION,
        title=paper["title"],
        abstract=paper["abstract"],
    )

    try:
        response = individual_model.generate(prompt)
        validation = validate_semantic_screening(response)

        if validation["valid"]:
            parsed = parse_semantic_screening(response)
            decision = parsed["decision"]
        else:
            decision = "EXCLUDE"
    except Exception:
        decision = "EXCLUDE"

    individual_results.append(decision)
    print(paper["id"], decision)

individual_time = time.perf_counter() - start

print("Individual calls:", individual_model.calls)
print(f"Individual time: {individual_time:.2f} seconds")


print("\n=== COMPARISON ===")
print(f"Batch: {batch_time:.2f} seconds")
print(f"Individual: {individual_time:.2f} seconds")

if individual_time > 0:
    improvement = (
        (individual_time - batch_time) / individual_time
    ) * 100
    print(f"Time improvement: {improvement:.2f}%")

batch_decisions = [
    result["decision"] for result in batch_results
]

print(
    "Decisions identical:",
    batch_decisions == individual_results,
)
