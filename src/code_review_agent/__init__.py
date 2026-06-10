"""code-review-agent: a multi-step code review agent on Anthropic Tool Use.

Packaged as a GitHub Action. Reads PR diff, explores codebase via tools,
posts review comments. Three-layer protection (max_steps / token budget /
loop detection) prevents runaway agent behavior.
"""
__version__ = "0.0.1"
