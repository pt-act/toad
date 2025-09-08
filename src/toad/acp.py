import asyncio
import json
import os
from typing import TypedDict, Required

from toad import jsonrpc


class ClientCapabilities(TypedDict, total=False):
    # https://agentclientprotocol.com/protocol/schema#clientcapabilities
    fs: Required[dict[str, bool]]
    terminal: bool


class AuthMethod(TypedDict, total=False):
    description: str | None
    id: Required[str]
    name: Required[str]


class InitializeResponse(TypedDict):
    agentCapabilities: dict[str, bool]
    authMethods: list[AuthMethod]
    protocolVersion: Required[int]


API = jsonrpc.API()


@API.method()
def initialize(
    protocolVersion: int, clientCapabilities: ClientCapabilities
) -> InitializeResponse: ...


class ACPAgent:
    def __init__(self, command: str) -> None:
        self.command = command
        self._agent_task: asyncio.Task | None = None
        self._task: asyncio.Task | None = None
        self._process: asyncio.subprocess.Process | None = None
        self.done_event = asyncio.Event()

        self.agent_capabilities: ClientCapabilities = {"fs": {}}
        self.auth_methods: list[AuthMethod] = []

    def start(self) -> None:
        self._agent_task = asyncio.create_task(self.run_client())

    def send(self, request: jsonrpc.Request) -> None:
        if self._process is None:
            raise RuntimeError("No process")
        stdin = self._process.stdin
        if stdin is not None:
            stdin.write(b"%s\n" % request.body_json)

    async def run_client(self) -> None:
        PIPE = asyncio.subprocess.PIPE

        process = self._process = await asyncio.create_subprocess_shell(
            self.command, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=os.environ
        )

        self._task = asyncio.create_task(self.run())

        assert process.stdout is not None
        assert process.stdin is not None

        # process.stdin.write(request.body_json + b"\n")
        # await process.stdin.drain()

        while line := await process.stdout.readline():
            response = json.loads(line.decode("utf-8"))
            if isinstance(response, dict):
                if "result" in response:
                    API.process_response(response)
                else:
                    print(response)

        print("exit")

    async def run(self) -> None:
        with API.request() as request:
            initialize_response = initialize(
                1,
                {
                    "fs": {
                        "readTextFile": True,
                        "writeTextFile": True,
                    },
                    "terminal": False,
                },
            )
        self.send(request)
        response = await initialize_response.wait()
        print("GOT RESPONSE")
        print(response)
        del request


if __name__ == "__main__":
    from rich import print

    async def run_agent():
        agent = ACPAgent("gemini --experimental-acp")
        agent.start()
        await agent.done_event.wait()

    asyncio.run(run_agent())
