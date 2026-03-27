"""
GitHub Scout agent for fetching and analyzing GitHub profile data.
Uses async httpx for GitHub API calls and textstat for README analysis.
"""

import re
import json
import base64
import logging
from typing import Optional, List, Dict, Any
import httpx
import textstat
from ..models.candidate import GitHubSignals, Repository, README
from ..utils.groq_client import groq_client
from ..config import (
    GITHUB_TOKEN, MAX_REPOS_TO_SCAN, README_SCORER_MODEL,
    README_MIN_WORDS, README_LOW_QUALITY_SCORE, README_MEDIUM_QUALITY_SCORE
)

logger = logging.getLogger(__name__)


class GitHubScout:
    """Agent for analyzing GitHub profiles and repositories."""

    def __init__(self):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async def analyze_github_profile(self, github_url: str) -> Optional[GitHubSignals]:
        """
        Analyze a GitHub profile and return comprehensive signals.

        Args:
            github_url: GitHub profile or repository URL

        Returns:
            GitHubSignals object or None if analysis fails
        """
        try:
            # Extract username from GitHub URL
            username = self._extract_username(github_url)
            if not username:
                logger.warning(f"Could not extract username from URL: {github_url}")
                return None

            logger.info(f"Analyzing GitHub profile for user: {username}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get user profile
                profile_data = await self._fetch_user_profile(client, username)
                if not profile_data:
                    return None

                # Get top repositories
                repositories = await self._fetch_top_repositories(client, username)

                # Analyze README files for each repository
                analyzed_repos = await self._analyze_repositories(client, username, repositories)

                return GitHubSignals(
                    username=username,
                    profile_url=f"https://github.com/{username}",
                    public_repos=profile_data.get('public_repos', 0),
                    followers=profile_data.get('followers', 0),
                    following=profile_data.get('following', 0),
                    total_stars=sum(repo['stargazers_count'] for repo in repositories),
                    repositories=analyzed_repos
                )

        except Exception as e:
            logger.error(f"GitHub profile analysis failed: {str(e)}")
            return None

    def _extract_username(self, github_url: str) -> Optional[str]:
        """
        Extract GitHub username from various GitHub URL formats.

        Args:
            github_url: GitHub URL

        Returns:
            GitHub username or None if extraction fails
        """
        if not github_url:
            return None

        # Clean the URL
        url = github_url.strip().lower()

        # Remove protocol if present
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)

        # Extract username patterns
        patterns = [
            r'github\.com/([^/\s\?]+)',  # github.com/username
            r'^([^/\s\?]+)$'  # Just username
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1)
                # Validate username format
                if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]){0,38}$', username):
                    return username

        return None

    async def _fetch_user_profile(self, client: httpx.AsyncClient, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user profile data from GitHub API.

        Args:
            client: HTTP client
            username: GitHub username

        Returns:
            User profile data or None if failed
        """
        try:
            url = f"https://api.github.com/users/{username}"
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"GitHub user not found: {username}")
                return None
            else:
                logger.warning(f"GitHub API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch user profile: {str(e)}")
            return None

    async def _fetch_top_repositories(self, client: httpx.AsyncClient, username: str) -> List[Dict[str, Any]]:
        """
        Fetch top repositories by stars for a user.

        Args:
            client: HTTP client
            username: GitHub username

        Returns:
            List of repository data
        """
        try:
            url = f"https://api.github.com/users/{username}/repos"
            params = {
                "type": "owner",
                "sort": "updated",
                "per_page": 100
            }

            response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                logger.warning(f"Failed to fetch repositories: {response.status_code}")
                return []

            repos = response.json()

            # Filter and sort by stars
            repos = [repo for repo in repos if not repo.get('fork', False)]
            repos.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)

            return repos[:MAX_REPOS_TO_SCAN]

        except Exception as e:
            logger.error(f"Failed to fetch repositories: {str(e)}")
            return []

    async def _analyze_repositories(self, client: httpx.AsyncClient, username: str,
                                  repositories: List[Dict[str, Any]]) -> List[Repository]:
        """
        Analyze repositories and their README files.

        Args:
            client: HTTP client
            username: GitHub username
            repositories: List of repository data

        Returns:
            List of analyzed Repository objects
        """
        analyzed_repos = []

        for repo_data in repositories:
            try:
                repo_name = repo_data['name']
                logger.info(f"Analyzing repository: {repo_name}")

                # Get languages
                languages = await self._fetch_repository_languages(client, username, repo_name)

                # Get README content
                readme_content = await self._fetch_readme_content(client, username, repo_name)

                # Analyze README if found
                readme_score = None
                originality_verdict = None

                if readme_content:
                    readme_analysis = await self._analyze_readme(readme_content)
                    readme_score = readme_analysis.final_score

                    # Get originality verdict from LLM if available
                    if readme_analysis.llm_score:
                        # This would come from the LLM response
                        originality_verdict = "original"  # Placeholder - would be extracted from LLM

                # Create Repository object
                repository = Repository(
                    name=repo_name,
                    description=repo_data.get('description'),
                    languages=languages,
                    stars=repo_data.get('stargazers_count', 0),
                    forks=repo_data.get('forks_count', 0),
                    readme_content=readme_content[:500] if readme_content else None,  # Truncate for storage
                    readme_score=readme_score,
                    originality_verdict=originality_verdict
                )

                analyzed_repos.append(repository)

            except Exception as e:
                logger.warning(f"Failed to analyze repository {repo_data.get('name', 'unknown')}: {str(e)}")
                continue

        return analyzed_repos

    async def _fetch_repository_languages(self, client: httpx.AsyncClient, username: str, repo_name: str) -> Dict[str, int]:
        """
        Fetch programming languages used in a repository.

        Args:
            client: HTTP client
            username: GitHub username
            repo_name: Repository name

        Returns:
            Dictionary of languages and their byte counts
        """
        try:
            url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                return {}

        except Exception as e:
            logger.warning(f"Failed to fetch languages for {repo_name}: {str(e)}")
            return {}

    async def _fetch_readme_content(self, client: httpx.AsyncClient, username: str, repo_name: str) -> Optional[str]:
        """
        Fetch README content from a repository.

        Args:
            client: HTTP client
            username: GitHub username
            repo_name: Repository name

        Returns:
            README content as string or None if not found
        """
        readme_files = ['README.md', 'readme.md', 'README.txt', 'README']

        for readme_file in readme_files:
            try:
                url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{readme_file}"
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    content_data = response.json()
                    if content_data.get('encoding') == 'base64':
                        content = base64.b64decode(content_data['content']).decode('utf-8')
                        return content

            except Exception as e:
                continue

        return None

    async def _analyze_readme(self, content: str) -> README:
        """
        Analyze README content using NLP heuristics and optionally LLM.

        Args:
            content: README content

        Returns:
            README analysis object
        """
        # Basic NLP analysis
        word_count = len(content.split())
        has_headers = '##' in content or '#' in content
        has_code_blocks = '```' in content or '`' in content

        # Apply heuristics first
        if word_count < README_MIN_WORDS:
            # Auto score low for very short READMEs
            return README(
                content=content,
                word_count=word_count,
                has_headers=has_headers,
                has_code_blocks=has_code_blocks,
                heuristic_score=README_LOW_QUALITY_SCORE,
                llm_score=None,
                final_score=README_LOW_QUALITY_SCORE
            )

        if not has_headers and not has_code_blocks:
            # Auto score medium for basic READMEs
            return README(
                content=content,
                word_count=word_count,
                has_headers=has_headers,
                has_code_blocks=has_code_blocks,
                heuristic_score=README_MEDIUM_QUALITY_SCORE,
                llm_score=None,
                final_score=README_MEDIUM_QUALITY_SCORE
            )

        # README passes heuristics - use LLM for detailed analysis
        try:
            llm_result = await self._score_readme_with_llm(content)
            return README(
                content=content,
                word_count=word_count,
                has_headers=has_headers,
                has_code_blocks=has_code_blocks,
                heuristic_score=None,
                llm_score=llm_result['readme_score'],
                final_score=llm_result['readme_score']
            )

        except Exception as e:
            logger.warning(f"LLM README scoring failed, using heuristic: {str(e)}")
            # Fallback to heuristic scoring
            heuristic_score = 6 if has_headers and has_code_blocks else 4
            return README(
                content=content,
                word_count=word_count,
                has_headers=has_headers,
                has_code_blocks=has_code_blocks,
                heuristic_score=heuristic_score,
                llm_score=None,
                final_score=heuristic_score
            )

    async def _score_readme_with_llm(self, content: str) -> Dict[str, Any]:
        """
        Score README using Groq LLM.

        Args:
            content: README content

        Returns:
            LLM scoring result
        """
        # Truncate README if too long
        if len(content) > 2000:
            content = content[:2000] + "\n\n[... TRUNCATED ...]"

        prompt_template = groq_client.load_prompt_template("readme_scorer.txt")
        full_prompt = f"{prompt_template}\n\n{content}"

        response = await groq_client.send_prompt(
            model=README_SCORER_MODEL,
            prompt=full_prompt,
            temperature=0.2,
            max_tokens=500,  # Limit response for README scoring
            json_mode=True,
            timeout=30  # Shorter timeout for README analysis
        )

        return response


# Instance for easy importing
github_scout = GitHubScout()