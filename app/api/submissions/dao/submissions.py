"""Submissions Data Access Object — raw database queries."""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import AssignmentStatus, ContestStatus, SubmissionVerdict
from app.database.models.bidding import ContestProblemAssignment
from app.database.models.contests import Contest, TeamContest
from app.database.models.problems import ContestProblem
from app.database.models.submissions import Submission, SubmissionTestResult
from app.database.models.teams import TeamMember

logger = logging.getLogger(__name__)


class SubmissionDAO:
    """Data Access Object for submission-related database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_contest(self, contest_id: str) -> Optional[Contest]:
        result = await self._session.execute(
            select(Contest).where(Contest.id == contest_id)
        )
        return result.scalar_one_or_none()

    async def get_contest_problem(
        self, contest_problem_id: str
    ) -> Optional[ContestProblem]:
        result = await self._session.execute(
            select(ContestProblem).where(ContestProblem.id == contest_problem_id)
        )
        return result.scalar_one_or_none()

    async def get_assignment(
        self, contest_problem_id: str, team_id: str
    ) -> Optional[ContestProblemAssignment]:
        """Get the assignment for a team on a specific contest problem."""
        result = await self._session.execute(
            select(ContestProblemAssignment).where(
                ContestProblemAssignment.contest_problem_id == contest_problem_id,
                ContestProblemAssignment.team_id == team_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_team_member(
        self, team_id: str, user_id: str
    ) -> Optional[TeamMember]:
        result = await self._session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_team_contest(
        self, team_id: str, contest_id: str
    ) -> Optional[TeamContest]:
        result = await self._session.execute(
            select(TeamContest).where(
                TeamContest.team_id == team_id,
                TeamContest.contest_id == contest_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Submission CRUD ───────────────────────────────────────────────────────

    async def create_submission(self, submission: Submission) -> Submission:
        self._session.add(submission)
        await self._session.commit()
        await self._session.refresh(submission)
        return submission

    async def update_submission(self, submission: Submission) -> Submission:
        self._session.add(submission)
        await self._session.commit()
        await self._session.refresh(submission)
        return submission

    async def get_submission_by_id(
        self, submission_id: str
    ) -> Optional[Submission]:
        result = await self._session.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def list_submissions_for_assignment(
        self, assignment_id: str
    ) -> list[Submission]:
        result = await self._session.execute(
            select(Submission)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def list_submissions_for_team_in_contest(
        self, team_id: str, contest_id: str
    ) -> list[Submission]:
        result = await self._session.execute(
            select(Submission)
            .where(
                Submission.team_id == team_id,
                Submission.contest_id == contest_id,
            )
            .order_by(Submission.submitted_at.desc())
        )
        return list(result.scalars().all())

    # ── Test Results ──────────────────────────────────────────────────────────

    async def create_test_results(
        self, results: list[SubmissionTestResult]
    ) -> list[SubmissionTestResult]:
        self._session.add_all(results)
        await self._session.commit()
        for r in results:
            await self._session.refresh(r)
        return results

    # ── Scoring (atomic) ──────────────────────────────────────────────────────

    async def mark_assignment_solved_and_add_score(
        self, assignment_id: str, team_id: str, contest_id: str, points: int
    ) -> None:
        """Atomically: assignment → SOLVED, team_contest.score += points."""
        # Update assignment status
        await self._session.execute(
            update(ContestProblemAssignment)
            .where(ContestProblemAssignment.id == assignment_id)
            .values(status=AssignmentStatus.SOLVED)
        )
        # Add points to team score
        await self._session.execute(
            update(TeamContest)
            .where(
                TeamContest.team_id == team_id,
                TeamContest.contest_id == contest_id,
            )
            .values(score=TeamContest.score + points)
        )
        await self._session.commit()
        logger.info(
            f"Assignment {assignment_id} → SOLVED, +{points} points for "
            f"team {team_id} in contest {contest_id}"
        )


# ── Dependency ────────────────────────────────────────────────────────────────


async def get_submission_dao(
    session: AsyncSession = Depends(get_db),
) -> SubmissionDAO:
    return SubmissionDAO(session)
