"""
Performance Benchmarking Suite for FinSight API
Measures latency, throughput, and resource usage

Usage:
    python tests/performance/benchmark.py --endpoint metrics --concurrency 50
    python tests/performance/benchmark.py --full-suite
"""

import asyncio
import time
import statistics
import argparse
from typing import List, Dict
import aiohttp
import psutil
import json
from datetime import datetime


class PerformanceBenchmark:
    """Benchmark runner for FinSight API"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "fsk_test"):
        self.base_url = base_url
        self.api_key = api_key
        self.results = {}

    async def measure_latency(self, endpoint: str, params: dict = None, num_requests: int = 100):
        """Measure endpoint latency"""
        latencies = []
        headers = {"X-API-Key": self.api_key}

        async with aiohttp.ClientSession() as session:
            for _ in range(num_requests):
                start = time.time()

                try:
                    async with session.get(
                        f"{self.base_url}{endpoint}",
                        params=params,
                        headers=headers
                    ) as response:
                        await response.read()
                        latency = (time.time() - start) * 1000  # ms

                        if response.status == 200:
                            latencies.append(latency)

                except Exception as e:
                    print(f"Request failed: {e}")

                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.01)

        return {
            "endpoint": endpoint,
            "requests": num_requests,
            "successful": len(latencies),
            "min_ms": min(latencies) if latencies else 0,
            "max_ms": max(latencies) if latencies else 0,
            "mean_ms": statistics.mean(latencies) if latencies else 0,
            "median_ms": statistics.median(latencies) if latencies else 0,
            "p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0,
            "p99_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else 0,
            "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
        }

    async def measure_throughput(self, endpoint: str, duration_seconds: int = 10):
        """Measure requests per second"""
        request_count = 0
        headers = {"X-API-Key": self.api_key}
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration_seconds:
                try:
                    async with session.get(
                        f"{self.base_url}{endpoint}",
                        headers=headers
                    ) as response:
                        await response.read()

                        if response.status == 200:
                            request_count += 1

                except Exception:
                    pass

        elapsed = time.time() - start_time
        rps = request_count / elapsed

        return {
            "endpoint": endpoint,
            "duration_seconds": duration_seconds,
            "total_requests": request_count,
            "requests_per_second": rps
        }

    async def measure_concurrent_load(self, endpoint: str, concurrency: int = 50, requests_per_client: int = 10):
        """Measure performance under concurrent load"""
        headers = {"X-API-Key": self.api_key}

        async def client_task():
            """Single client making multiple requests"""
            latencies = []
            async with aiohttp.ClientSession() as session:
                for _ in range(requests_per_client):
                    start = time.time()

                    try:
                        async with session.get(
                            f"{self.base_url}{endpoint}",
                            headers=headers
                        ) as response:
                            await response.read()
                            latency = (time.time() - start) * 1000

                            if response.status == 200:
                                latencies.append(latency)

                    except Exception:
                        pass

            return latencies

        # Run concurrent clients
        start_time = time.time()
        tasks = [client_task() for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # Aggregate results
        all_latencies = [lat for client_lats in results for lat in client_lats]
        total_requests = sum(len(client_lats) for client_lats in results)

        return {
            "endpoint": endpoint,
            "concurrency": concurrency,
            "total_requests": total_requests,
            "successful_requests": len(all_latencies),
            "duration_seconds": elapsed,
            "requests_per_second": len(all_latencies) / elapsed if elapsed > 0 else 0,
            "mean_latency_ms": statistics.mean(all_latencies) if all_latencies else 0,
            "p95_latency_ms": statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) > 20 else 0
        }

    def measure_resource_usage(self, duration_seconds: int = 10):
        """Measure server resource usage"""
        process = psutil.Process()

        cpu_percentages = []
        memory_usage = []

        for _ in range(duration_seconds):
            cpu_percentages.append(process.cpu_percent(interval=1))
            memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB

        return {
            "duration_seconds": duration_seconds,
            "avg_cpu_percent": statistics.mean(cpu_percentages),
            "max_cpu_percent": max(cpu_percentages),
            "avg_memory_mb": statistics.mean(memory_usage),
            "max_memory_mb": max(memory_usage)
        }

    async def benchmark_endpoint(self, endpoint: str, params: dict = None):
        """Run full benchmark suite for an endpoint"""
        print(f"\n{'='*60}")
        print(f"Benchmarking: {endpoint}")
        print(f"{'='*60}")

        # 1. Latency test
        print("\n1. Latency Test (100 requests)...")
        latency_results = await self.measure_latency(endpoint, params, num_requests=100)

        print(f"   Min: {latency_results['min_ms']:.2f}ms")
        print(f"   Mean: {latency_results['mean_ms']:.2f}ms")
        print(f"   Median: {latency_results['median_ms']:.2f}ms")
        print(f"   P95: {latency_results['p95_ms']:.2f}ms")
        print(f"   P99: {latency_results['p99_ms']:.2f}ms")
        print(f"   Max: {latency_results['max_ms']:.2f}ms")

        # 2. Throughput test
        print("\n2. Throughput Test (10 seconds)...")
        throughput_results = await self.measure_throughput(endpoint, duration_seconds=10)

        print(f"   Requests/sec: {throughput_results['requests_per_second']:.2f}")
        print(f"   Total requests: {throughput_results['total_requests']}")

        # 3. Concurrent load test
        print("\n3. Concurrent Load Test (50 concurrent users)...")
        concurrent_results = await self.measure_concurrent_load(endpoint, concurrency=50, requests_per_client=10)

        print(f"   Concurrency: {concurrent_results['concurrency']}")
        print(f"   Requests/sec: {concurrent_results['requests_per_second']:.2f}")
        print(f"   Mean latency: {concurrent_results['mean_latency_ms']:.2f}ms")
        print(f"   P95 latency: {concurrent_results['p95_latency_ms']:.2f}ms")

        return {
            "endpoint": endpoint,
            "latency": latency_results,
            "throughput": throughput_results,
            "concurrent_load": concurrent_results
        }

    async def run_full_suite(self):
        """Run benchmarks for all endpoints"""
        print("\n" + "="*60)
        print("FINSIGHT API - FULL PERFORMANCE BENCHMARK SUITE")
        print("="*60)

        endpoints = [
            ("/health", None),
            ("/api/v1/pricing", None),
            ("/api/v1/metrics/available", None),
            ("/api/v1/metrics", {"ticker": "AAPL", "metrics": "revenue"}),
            ("/api/v1/companies/search", {"q": "apple"}),
        ]

        all_results = {}

        for endpoint, params in endpoints:
            result = await self.benchmark_endpoint(endpoint, params)
            all_results[endpoint] = result
            await asyncio.sleep(2)  # Cool down between tests

        # Generate summary
        self.print_summary(all_results)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"\n✓ Results saved to {filename}")

        return all_results

    def print_summary(self, results: Dict):
        """Print summary of all benchmark results"""
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("")
        print(f"{'Endpoint':<40} {'Mean (ms)':<12} {'P95 (ms)':<12} {'RPS':<10}")
        print("-"*60)

        for endpoint, data in results.items():
            mean_lat = data['latency']['mean_ms']
            p95_lat = data['latency']['p95_ms']
            rps = data['throughput']['requests_per_second']

            print(f"{endpoint:<40} {mean_lat:<12.2f} {p95_lat:<12.2f} {rps:<10.2f}")

        print("")

        # Performance grades
        print("Performance Grades:")
        print("-" * 60)

        for endpoint, data in results.items():
            p95 = data['latency']['p95_ms']

            if p95 < 100:
                grade = "A (Excellent)"
            elif p95 < 250:
                grade = "B (Good)"
            elif p95 < 500:
                grade = "C (Acceptable)"
            elif p95 < 1000:
                grade = "D (Slow)"
            else:
                grade = "F (Unacceptable)"

            print(f"{endpoint:<40} {grade}")


async def main():
    parser = argparse.ArgumentParser(description="FinSight API Performance Benchmark")
    parser.add_argument("--host", default="http://localhost:8000", help="API host")
    parser.add_argument("--api-key", default="fsk_test", help="API key for testing")
    parser.add_argument("--endpoint", help="Specific endpoint to benchmark")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent users")
    parser.add_argument("--full-suite", action="store_true", help="Run full benchmark suite")

    args = parser.parse_args()

    benchmark = PerformanceBenchmark(base_url=args.host, api_key=args.api_key)

    if args.full_suite:
        await benchmark.run_full_suite()
    elif args.endpoint:
        await benchmark.benchmark_endpoint(args.endpoint)
    else:
        print("Please specify --endpoint or --full-suite")


if __name__ == "__main__":
    asyncio.run(main())
