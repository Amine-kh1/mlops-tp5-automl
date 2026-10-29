"""Bloc D : un appel témoin, 10 échauffements, 200 appels valides chronométrés."""
import argparse
import statistics
import time
from datetime import datetime, timezone
import requests
from common import REPORTS, write_json

CORPS = {"dataframe_records": [{"montant": 8500.0, "anciennete": 3, "freq_24h": 9, "nuit": 1}]}


def measure(port, repetition):
    url = f"http://127.0.0.1:{port}/invocations"

    def call(body=CORPS):
        response = requests.post(url, json=body, timeout=10)
        response.raise_for_status()
        result = response.json()
        assert result.get("predictions") in ([0], [1]), result
        return response, result

    response, first = call()
    print(f"port {port} | réponse : {response.status_code} {first}")
    for _ in range(10):
        call()
    latencies = []
    for _ in range(200):
        start = time.perf_counter()
        call()
        latencies.append((time.perf_counter() - start) * 1000)
    result = {"port": port, "repetition": repetition, "utc": datetime.now(timezone.utc).isoformat(),
              "first_status": response.status_code, "first_response": first, "warmups": 10,
              "n": 200, "median_ms": statistics.median(latencies),
              "p95_ms": statistics.quantiles(latencies, n=20, method="exclusive")[18],
              "latencies_ms": latencies, "connection": "requests.post sans Session persistante"}
    write_json(REPORTS / f"latence_{port}_{repetition}.json", result)
    print(f"port {port} | mesure {repetition} | médiane : {result['median_ms']:.3f} ms | p95 : {result['p95_ms']:.3f} ms | n=200")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, nargs="?", default=8100, choices=[8100, 8101])
    parser.add_argument("--repetition", type=int, default=1)
    args = parser.parse_args()
    measure(args.port, args.repetition)


if __name__ == "__main__":
    main()
