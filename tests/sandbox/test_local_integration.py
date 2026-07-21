from typing import cast

import agent.integrations.local as local_mod


class _StubLocalShellBackend:
    def __init__(self, *, root_dir, virtual_mode, env, inherit_env):
        self.root_dir = root_dir
        self.virtual_mode = virtual_mode
        self.env = env
        self.inherit_env = inherit_env


def test_create_local_sandbox_creates_missing_root_dir(monkeypatch, tmp_path):
    root = tmp_path / "nested" / "openswe-sandbox"
    monkeypatch.setenv("LOCAL_SANDBOX_ROOT_DIR", str(root))
    monkeypatch.setattr(local_mod, "LocalAuthenticatedShellBackend", _StubLocalShellBackend)

    backend = local_mod.create_local_sandbox()

    assert root.is_dir()
    stub = cast(_StubLocalShellBackend, backend)
    assert stub.root_dir == str(root)
    assert stub.virtual_mode is True
    assert isinstance(stub.env, local_mod._LocalSandboxEnvironment)
    assert stub.inherit_env is False


def test_create_local_sandbox_defaults_to_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("LOCAL_SANDBOX_ROOT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(local_mod, "LocalAuthenticatedShellBackend", _StubLocalShellBackend)

    backend = local_mod.create_local_sandbox()

    stub = cast(_StubLocalShellBackend, backend)
    assert stub.root_dir == str(tmp_path)
    assert stub.virtual_mode is True


def test_local_sandbox_environment_tracks_refreshed_github_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_SANDBOX_ROOT_DIR", str(tmp_path))
    monkeypatch.setenv("SANDBOX_TYPE", "local")

    backend = local_mod.create_local_sandbox()
    local_mod.configure_local_sandbox_github_token(backend, "refreshed-token")

    result = backend.execute('printf "%s:%s" "$OPEN_SWE_GITHUB_TOKEN" "$GH_TOKEN"')

    assert result.exit_code == 0
    assert result.output == "refreshed-token:refreshed-token"


def test_local_sandbox_configures_ephemeral_github_git_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_SANDBOX_ROOT_DIR", str(tmp_path))
    monkeypatch.setenv("SANDBOX_TYPE", "local")

    backend = local_mod.create_local_sandbox()
    local_mod.configure_local_sandbox_github_token(backend, "installation-token")

    helper = backend.execute(
        "git config --get-urlmatch credential.helper "
        "https://github.com/HideSmithAI/hero-ai-orchestrator.git"
    )
    rewrites = backend.execute("git config --get-all url.https://github.com/.insteadOf")

    assert helper.exit_code == 0
    assert helper.output == "!gh auth git-credential\n"
    assert rewrites.exit_code == 0
    assert rewrites.output.splitlines() == [
        "git@github.com:",
        "ssh://git@github.com/",
        "git://github.com/",
    ]


def test_local_sandbox_tokens_are_isolated_per_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_SANDBOX_ROOT_DIR", str(tmp_path))

    first = local_mod.create_local_sandbox()
    second = local_mod.create_local_sandbox()
    local_mod.configure_local_sandbox_github_token(first, "repo-a-token")
    local_mod.configure_local_sandbox_github_token(second, "repo-b-token")

    first_result = first.execute('printf %s "$OPEN_SWE_GITHUB_TOKEN"')
    second_result = second.execute('printf %s "$OPEN_SWE_GITHUB_TOKEN"')

    assert first_result.output == "repo-a-token"
    assert second_result.output == "repo-b-token"
