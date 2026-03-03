import os
import requests
import urllib.parse
import urllib.request
from pathlib import Path

from trudag.dotstop.core.reference.references import BaseReference, FileReference

class WebReference(BaseReference):
  def __init__(self, url: str) -> None:
        """
        References to arbitrary web pages.

        This reference fetches the page at the given URL using `requests` and exposes
        its content via the `content` property. The content is returned as UTF-8
        encoded bytes. Optional line anchors can be embedded in the URL (e.g.
        "https://example.com/file.txt#L10" or "https://example.com/file.txt#L5-L15")
        to highlight specific lines in the returned content with markdown blockquote
        prefix (> ).

        Args:
            url (str): URL of the webpage to reference. Must be a valid HTTP or HTTPS URL.
                       May optionally include line anchors like #L10 or #L10-L20.

        Notes:
            Network errors will raise `requests.RequestException` when accessing `content`.
            Line anchors are stripped before fetching but used to highlight lines in the result.
        """
        # allow optional line anchor embedded in the URL (e.g. "http://example.com/file#L12" or
        # "http://example.com/file#L5-L10"). record the bounds and strip the anchor before
        # passing to requests.get() so the URL is valid.
        start: int | None = None
        end: int | None = None
        if "#L" in url:
            base, anchor = url.split("#L", 1)
            if "-L" in anchor:
                a, b = anchor.split("-L", 1)
                try:
                    start = int(a)
                except ValueError:
                    start = None
                try:
                    end = int(b)
                except ValueError:
                    end = start
            else:
                try:
                    start = int(anchor)
                except ValueError:
                    start = None
            url = base
        self._url = url
        self._start = start
        self._end = end
  

  @classmethod
  def type(cls) -> str:
    return "webpage"

  @property
  def content(self) -> bytes:
    response = requests.get(self._url)
    raw = response.text.encode('utf-8')

    # if no anchor present just return raw bytes
    if self._start is None:
      return raw

    # highlight selected lines in markdown style by prefixing with '> '
    text = response.text
    lines = text.splitlines(keepends=True)
    start_val: int = self._start  # type: ignore[assignment]
    start_idx = max(start_val - 1, 0)
    end_val: int = self._end if self._end is not None else start_val  # type: ignore[assignment]
    end_idx = min(end_val, len(lines))
    out_lines: list[str] = []
    for idx, line in enumerate(lines, start=1):
      if start_idx <= idx - 1 < end_idx:
        out_lines.append(f"> {line}")
      else:
        out_lines.append(line)
    return "".join(out_lines).encode('utf-8')

  def as_markdown(self, filepath: None | str = None) -> str:
    return f"`{self._url}`"


class DownloadUrlReference(BaseReference):
  def __init__(self, download_url: str) -> None:
        """
        References a file download URL, e.g. pointing to a GitHub release artifact.

        This reference simply holds the download URL, and renders a useful markdown representation.

        Args:
            download_url (str): URL of the file to reference.

        Notes:
            No network access/file download is performed by this renderer.
        """
        self._download_url = download_url

  @classmethod
  def type(cls) -> str:
    return "download_url"

  @property
  def content(self) -> bytes:
    return self._download_url.encode()

  def as_markdown(self, filepath: None | str = None) -> str:
    return f"`{self._download_url}`"


class OpenFastTraceReference(BaseReference):
  def __init__(self, requirement_id: str) -> None:
        """
        References to an OpenFastTrace requirement idenfier.

        This will do something useful with this requirement id.

        Args:
            requirement_id (str): OpenFastTrace requirement identifier.

        Notes:
            tbd.
        """
        self._requirement_id = requirement_id
  

  @classmethod
  def type(cls) -> str:
    return "openfasttrace"

  @property
  def content(self) -> bytes:
    # todo
    return self._requirement_id.encode()

  def as_markdown(self, filepath: None | str = None) -> str:
    return f"`{self._requirement_id}`"



class GithubFileReference(FileReference):
    DEFAULT_TOKEN_ENV_VAR = "GITHUB_TOKEN"

    def __init__(
        self,
        project: str,
        repository: str,
        path: str,
        public: bool = True,
        ref: str = "main",
        token: str = DEFAULT_TOKEN_ENV_VAR,
        **kwargs,
    ) -> None:
        """
        References to Artifacts that are regular files in a GitHub repository.

        For acessing non-public repositories, a valid [github token](https://docs.github.com/en/actions/concepts/security/github_token) 
        with sufficient read permissions must be available in the current environment.
        Several attempts are made to get a token, with the following precedence:

        1. User-specified `token` argument
        2. `$GITHUB_TOKEN`

        Args:
            repository (str): repository id
            path (str): Path to the Artifact, relative to the root of the repository
            public (bool): Indicate whether the repository is public (defaults to `true`, non-public repos require an access token to be set)
            ref (str, optional): Tag, branch or sha (defaults to `main`)
            token (str, optional): Environmental variable containing a suitable access token. Defaults to "GITHUB_TOKEN".
        """
        self._repository = repository
        # allow optional line anchor embedded in the path (e.g. "foo.txt#L12" or
        # "foo.txt#L5-L10"). record the bounds and strip the anchor before
        # converting to Path so the downloader still sees a valid filename.
        start: int | None = None
        end: int | None = None
        if "#L" in path:
            base, anchor = path.split("#L", 1)
            if "-L" in anchor:
                a, b = anchor.split("-L", 1)
                try:
                    start = int(a)
                except ValueError:
                    start = None
                try:
                    end = int(b)
                except ValueError:
                    end = start
            else:
                try:
                    start = int(anchor)
                except ValueError:
                    start = None
            path = base
        self._path = Path(path)
        self._start = start
        self._end = end
        self._public = public
        self._ref = ref
        self._token_env_var = token
        self._url = "https://github.com"

    @classmethod
    def type(cls) -> str:
        return "github"

    def _get_query(self) -> str:
        # https://github.com/<your_Github_username>/<your_repository_name>/blob/<branch_name>/<file_name>.<extension_name>
        query = f"{self._url}/{self._repository}/blob/{self._ref}/{urllib.parse.quote(str(self._path), safe='')}"
        if getattr(self, '_start', None) is not None:
            if self._end is None or self._end == self._start:
                query += f"#L{self._start}"
            else:
                query += f"#L{self._start}-L{self._end}"
        return query

    @property
    def content(self) -> bytes:
        query = self._get_query()
        try:
            req = urllib.request.Request(query)
        except Exception as exc:
            raise ReferenceError(f"Parse error for URL: {query}") from exc
        if not self._public:
            token = os.environ.get(self._token_env_var)
            if not token:
                token = os.environ.get(GithubFileReference.DEFAULT_TOKEN_ENV_VAR)
            if not token:
                err_msg = f"Access token must be set in ${self._token_env_var} or ${GithubFileReference.DEFAULT_TOKEN_ENV_VAR} for url {query}"
                raise ReferenceError(err_msg)
            req.add_header('Authorization', 'Bearer %s' % token)
        try:
            resp = urllib.request.urlopen(req)
        except Exception as exc:
            raise ReferenceError(f"Could not GET: {query}") from exc
        
        raw = resp.read()

        # if no anchor present just return raw bytes
        if getattr(self, '_start', None) is None:
            return raw

        start_val: int = self._start  # type: ignore[assignment]
        # highlight selected lines in markdown style by prefixing with '> '
        try:
            text = raw.decode('utf-8')
        except Exception:
            text = raw.decode('utf-8', errors='replace')
        lines = text.splitlines(keepends=True)
        start_idx = max(start_val - 1, 0)
        end_val: int = self._end if self._end is not None else start_val  # type: ignore[assignment]
        end_idx = min(end_val, len(lines))
        out_lines: list[str] = []
        for idx, line in enumerate(lines, start=1):
            if start_idx <= idx - 1 < end_idx:
                out_lines.append(f"> {line}")
            else:
                out_lines.append(line)
        return "".join(out_lines).encode('utf-8')

    @property
    def extension(self) -> str:
        return self._path.suffix

    def __str__(self) -> str:
        return self._get_query()
