<!--
Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
Agent Skills expose each skill's name and description for matching, and load the body only when a skill is used.
Claude Code lists those entries in the skill tool as an <available_skills> block of <skill><name> and <description>: https://code.claude.com/docs/en/skills
-->
Check whether an available skill matches the task. When one does, load it with this tool before starting the work.

<available_skills>
{available_skills}
</available_skills>
