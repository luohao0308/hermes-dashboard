"""Multi-model consensus engine for filtering review findings."""

from difflib import SequenceMatcher

from .models import ReviewFinding


def _title_similarity(a: str, b: str) -> float:
    """Quick sequence-matcher ratio between two titles."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class ConsensusEngine:
    """Filters findings to only keep those agreed upon by multiple models."""

    def __init__(
        self,
        min_agreement: int = 2,
        similarity_threshold: float = 0.55,
        line_proximity: int = 5,
    ) -> None:
        self._min_agreement = min_agreement
        self._similarity_threshold = similarity_threshold
        self._line_proximity = line_proximity

    def _are_similar(self, a: ReviewFinding, b: ReviewFinding) -> bool:
        """Check if two findings refer to the same issue."""
        if a.file_path != b.file_path:
            return False
        if abs(a.line_number - b.line_number) > self._line_proximity:
            return False
        return _title_similarity(a.title, b.title) >= self._similarity_threshold

    def find_consensus(
        self,
        model_results: dict[str, list[ReviewFinding]],
    ) -> list[ReviewFinding]:
        """Return only findings on which at least min_agreement models agree.

        Args:
            model_results: Mapping of provider name -> list of findings.

        Returns:
            Filtered and deduplicated findings with updated confidence and
            providers_agreed fields, sorted by severity then confidence.
        """
        all_findings: list[tuple[str, ReviewFinding]] = []
        for provider, findings in model_results.items():
            for f in findings:
                all_findings.append((provider, f))

        # Group similar findings together
        groups: list[list[tuple[str, ReviewFinding]]] = []
        used = set()
        for i, (prov_a, finding_a) in enumerate(all_findings):
            if i in used:
                continue
            group = [(prov_a, finding_a)]
            used.add(i)
            for j, (prov_b, finding_b) in enumerate(all_findings):
                if j in used:
                    continue
                if self._are_similar(finding_a, finding_b):
                    group.append((prov_b, finding_b))
                    used.add(j)
            groups.append(group)

        # Keep groups with enough agreement
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "style": 4}
        consensus_findings: list[ReviewFinding] = []
        for group in groups:
            if len(group) < self._min_agreement:
                continue
            providers = [prov for prov, _ in group]
            base = group[0][1]
            consensus_findings.append(
                base.model_copy(
                    update={
                        "providers_agreed": providers,
                        "confidence": round(len(group) / len(model_results), 2),
                    }
                )
            )

        consensus_findings.sort(
            key=lambda f: (severity_order.get(f.severity, 5), -f.confidence)
        )
        return consensus_findings
