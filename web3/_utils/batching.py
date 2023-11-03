class BatchRequestContextManager:
    def __init__(self, web3):
        self.web3 = web3
        self._requests = []

    async def __aenter__(self):
        self.web3._request_lock = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.web3._request_lock = False

    def add(self, request):
        self._requests.append(request)

    async def execute(self):
        return await self.web3.manager.async_make_batch_request(self._requests)
