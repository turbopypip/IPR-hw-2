from uuid import uuid4

from locust import HttpUser, between, task


class ShortistUser(HttpUser):
    wait_time = between(0.1, 1.0)

    @task(5)
    def create_random_link(self):
        suffix = uuid4().hex
        with self.client.post(
            "/links/shorten",
            json={
                "original_url": f"https://example.com/load/{suffix}",
                "expire_at": None,
            },
            name="/links/shorten",
            catch_response=True,
        ) as response:
            self._assert_link_created(response)

    @task(1)
    def create_custom_alias(self):
        alias = f"load{uuid4().hex[:12]}"
        with self.client.post(
            "/links/shorten",
            json={
                "original_url": f"https://example.com/custom/{alias}",
                "custom_alias": alias,
                "expire_at": None,
            },
            name="/links/shorten custom_alias",
            catch_response=True,
        ) as response:
            self._assert_link_created(response)

    @staticmethod
    def _assert_link_created(response):
        if response.status_code != 200:
            response.failure(f"expected 200, got {response.status_code}")
            return

        short_id = response.json().get("short_id")
        if not short_id:
            response.failure("response has no short_id")
