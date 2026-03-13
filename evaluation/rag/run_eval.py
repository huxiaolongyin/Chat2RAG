import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from evaluation.rag.evaluator import AggregatedResults, RetrievalEvaluator

DEFAULT_DATASET = "evaluation/data/KUAKE-IR/subset/eval_dataset.json"
DEFAULT_COLLECTION = "eval_mix"
DEFAULT_OUTPUT_DIR = "evaluation/rag/results"


async def run_evaluation(
    dataset_path: str,
    collection_name: str,
    top_k_values: list[int],
    output_dir: str,
    save_results: bool = True,
) -> AggregatedResults:
    evaluator = RetrievalEvaluator(
        collection_name=collection_name,
        top_k_values=top_k_values,
        score_threshold=0.0,
    )

    results = await evaluator.evaluate(dataset_path)

    report = evaluator.generate_report(results)
    print("\n" + report)

    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"eval_results_{timestamp}.json"
        evaluator.save_results(results, str(output_path))

    return results


def main():
    parser = argparse.ArgumentParser(description="RAG Retrieval Evaluation")
    parser.add_argument(
        "--dataset",
        "-d",
        type=str,
        default=DEFAULT_DATASET,
        help=f"Path to evaluation dataset (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--collection",
        "-c",
        type=str,
        default=DEFAULT_COLLECTION,
        help=f"Qdrant collection name (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        nargs="+",
        default=[1, 3, 5, 10],
        help="K values for Hit@K, Recall@K, NDCG@K (default: 1 3 5 10)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for results (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save detailed results to file",
    )

    args = parser.parse_args()

    asyncio.run(
        run_evaluation(
            dataset_path=args.dataset,
            collection_name=args.collection,
            top_k_values=args.top_k,
            output_dir=args.output,
            save_results=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
