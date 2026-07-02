from typing import Any, Dict, List


class AthenaBrowserAgent:
    """
    ATHENA Browser Agent

    Plans future browser operations in simulation mode only. It never opens,
    controls, logs into, or automates a browser.
    """

    def plan(
        self,
        action_plan: Dict[str, Any],
        execution: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        required = self._browser_required(
            action_plan=action_plan,
            execution=execution,
            decision=decision,
        )
        browser_actions = self._browser_actions(action_plan) if required else []

        for index, action in enumerate(browser_actions, start=1):
            action["step"] = index

        return {
            "required": required,
            "mode": "simulation",
            "browser_actions": browser_actions,
            "estimated_pages": self._estimated_pages(browser_actions),
            "summary": self._summary(required=required, browser_actions=browser_actions),
        }

    def _browser_required(
        self,
        action_plan: Dict[str, Any],
        execution: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> bool:
        action_text = " ".join(
            str(step.get("action", ""))
            for step in action_plan.get("steps", []) or []
        ).lower()
        blocked_text = " ".join(execution.get("blocked_actions", []) or []).lower()
        approval_text = " ".join(execution.get("approval_required_for", []) or []).lower()

        return any(
            term in f"{action_text} {blocked_text} {approval_text}"
            for term in [
                "portal",
                "login",
                "tender",
                "submit",
                "upload",
                "download",
                "website",
            ]
        )

    def _browser_actions(self, action_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = [
            {
                "step": 0,
                "action": "Open Tender Portal",
                "approval_required": True,
            },
            {
                "step": 0,
                "action": "Authenticate",
                "approval_required": True,
            },
            {
                "step": 0,
                "action": "Search Tender",
                "approval_required": True,
            },
        ]

        planned_actions = " ".join(
            str(step.get("action", ""))
            for step in action_plan.get("steps", []) or []
        ).lower()

        if "download" in planned_actions:
            actions.append(
                {
                    "step": 0,
                    "action": "Download",
                    "approval_required": True,
                }
            )

        if "upload" in planned_actions or "submit tender" in planned_actions:
            actions.append(
                {
                    "step": 0,
                    "action": "Upload",
                    "approval_required": True,
                }
            )

        if "submit tender" in planned_actions:
            actions.append(
                {
                    "step": 0,
                    "action": "Submit",
                    "approval_required": True,
                }
            )

        actions.append(
            {
                "step": 0,
                "action": "Verify",
                "approval_required": True,
            }
        )
        actions.append(
            {
                "step": 0,
                "action": "Logout",
                "approval_required": True,
            }
        )

        return self._dedupe_actions(actions)

    def _estimated_pages(self, browser_actions: List[Dict[str, Any]]) -> int:
        if not browser_actions:
            return 0
        return max(1, len(browser_actions))

    def _summary(self, required: bool, browser_actions: List[Dict[str, Any]]) -> str:
        if not required:
            return "Browser interaction is not currently required. No browser actions have been executed."

        return "Browser interaction will eventually be required for tender or portal activity. No browser actions have been executed."

    def _dedupe_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped = []
        seen = set()
        for action in actions:
            key = action["action"].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(action)
        return deduped
