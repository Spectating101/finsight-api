"""
Load Testing Suite for FinSight API
Tests performance under various load conditions

Requirements:
    pip install locust

Usage:
    # Run from command line:
    locust -f tests/performance/test_load.py --host=http://localhost:8000

    # Or run headless:
    locust -f tests/performance/test_load.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 1m --headless
"""

import time
import random
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


# Test configuration
TEST_API_KEY = "fsk_test_load_testing_key_12345"
COMMON_TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM", "XOM", "JNJ", "WMT"]
COMMON_METRICS = ["revenue", "net_income", "total_assets", "total_debt"]


class APIUser(FastHttpUser):
    """
    Simulates a typical API user
    - Fetches metrics for various companies
    - Checks pricing info
    - Views available metrics
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    host = "http://localhost:8000"

    def on_start(self):
        """Called when a user starts"""
        self.headers = {"X-API-Key": TEST_API_KEY}

    @task(10)  # Weight: 10 (most common operation)
    def get_metrics(self):
        """Fetch financial metrics"""
        ticker = random.choice(COMMON_TICKERS)
        metrics = random.sample(COMMON_METRICS, k=random.randint(1, 3))

        with self.client.get(
            f"/api/v1/metrics?ticker={ticker}&metrics={','.join(metrics)}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(3)  # Weight: 3
    def search_companies(self):
        """Search for companies"""
        queries = ["apple", "tesla", "microsoft", "bank"]
        query = random.choice(queries)

        with self.client.get(
            f"/api/v1/companies/search?q={query}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/companies/search"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(2)  # Weight: 2
    def get_company_details(self):
        """Get company details"""
        ticker = random.choice(COMMON_TICKERS)

        with self.client.get(
            f"/api/v1/companies/{ticker}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/companies/{ticker}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(1)  # Weight: 1 (least common)
    def list_available_metrics(self):
        """List available metrics"""
        with self.client.get(
            "/api/v1/metrics/available",
            catch_response=True,
            name="/api/v1/metrics/available"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(1)
    def get_pricing(self):
        """Get pricing information (public endpoint)"""
        with self.client.get(
            "/api/v1/pricing",
            catch_response=True,
            name="/api/v1/pricing"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(1)
    def health_check(self):
        """Health check"""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Unhealthy")


class HeavyUser(FastHttpUser):
    """
    Simulates a heavy API user (enterprise tier)
    - Makes more frequent requests
    - Fetches more metrics per request
    """

    wait_time = between(0.5, 1.5)  # Faster requests
    host = "http://localhost:8000"

    def on_start(self):
        self.headers = {"X-API-Key": TEST_API_KEY}

    @task
    def batch_metrics(self):
        """Fetch multiple metrics for multiple companies"""
        tickers = random.sample(COMMON_TICKERS, k=3)

        for ticker in tickers:
            with self.client.get(
                f"/api/v1/metrics?ticker={ticker}&metrics=revenue,net_income,total_assets",
                headers=self.headers,
                catch_response=True,
                name="/api/v1/metrics [batch]"
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed with status {response.status_code}")
                    break


class SpikeTrafficUser(FastHttpUser):
    """
    Simulates spike traffic (sudden burst of users)
    Use with: --users 500 --spawn-rate 50 --run-time 2m
    """

    wait_time = between(0.1, 0.5)  # Very fast requests
    host = "http://localhost:8000"

    def on_start(self):
        self.headers = {"X-API-Key": TEST_API_KEY}

    @task
    def rapid_requests(self):
        """Make rapid consecutive requests"""
        ticker = random.choice(COMMON_TICKERS)

        with self.client.get(
            f"/api/v1/metrics?ticker={ticker}&metrics=revenue",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/metrics [spike]"
        ) as response:
            if response.status_code == 429:
                # Rate limiting is expected during spikes
                response.success()
            elif response.status_code == 200:
                response.success()


# Custom statistics tracking
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics"""
    if exception:
        return

    # Track slow requests (>1s)
    if response_time > 1000:
        print(f"Slow request detected: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("="*60)
    print("Load Test Starting")
    print(f"Target: {environment.host}")
    print("="*60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("="*60)
    print("Load Test Complete")
    print("="*60)

    stats = environment.stats.total

    print(f"Total Requests: {stats.num_requests}")
    print(f"Total Failures: {stats.num_failures}")
    print(f"Failure Rate: {stats.fail_ratio * 100:.2f}%")
    print(f"Median Response Time: {stats.median_response_time}ms")
    print(f"95th Percentile: {stats.get_response_time_percentile(0.95)}ms")
    print(f"99th Percentile: {stats.get_response_time_percentile(0.99)}ms")
    print(f"Requests/sec: {stats.total_rps:.2f}")


# Scenarios for different load patterns
class LoadTestScenarios:
    """
    Pre-configured load test scenarios

    Usage:
        # Normal load (100 users ramping over 30 seconds)
        locust -f tests/performance/test_load.py --users 100 --spawn-rate 3 --run-time 5m

        # Stress test (500 users, aggressive ramp)
        locust -f tests/performance/test_load.py --users 500 --spawn-rate 50 --run-time 10m

        # Spike test (sudden 1000 users)
        locust -f tests/performance/test_load.py --users 1000 --spawn-rate 100 --run-time 2m

        # Endurance test (steady 200 users for 1 hour)
        locust -f tests/performance/test_load.py --users 200 --spawn-rate 10 --run-time 1h
    """

    NORMAL_LOAD = {
        "users": 100,
        "spawn_rate": 3,
        "run_time": "5m",
        "description": "Normal production load"
    }

    STRESS_TEST = {
        "users": 500,
        "spawn_rate": 50,
        "run_time": "10m",
        "description": "Stress test to find breaking point"
    }

    SPIKE_TEST = {
        "users": 1000,
        "spawn_rate": 100,
        "run_time": "2m",
        "description": "Sudden traffic spike"
    }

    ENDURANCE_TEST = {
        "users": 200,
        "spawn_rate": 10,
        "run_time": "1h",
        "description": "Long-running endurance test"
    }
