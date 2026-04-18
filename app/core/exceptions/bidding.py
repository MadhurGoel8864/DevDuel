"""Bidding domain exceptions."""

from typing import Optional

from app.core.exceptions.base import AppException


class AuctionNotFoundException(AppException):
    """Raised when a problem auction is not found. HTTP 404."""

    def __init__(self, auction_id: Optional[str] = None, message: Optional[str] = None):
        details = {"auction_id": auction_id} if auction_id else None
        super().__init__(
            code="AUCTION_NOT_FOUND",
            message=message
            or (
                f"Auction with ID '{auction_id}' not found"
                if auction_id
                else "Auction not found"
            ),
            status_code=404,
            details=details,
        )


class AuctionAlreadyActiveException(AppException):
    """Raised when trying to start an auction while one is already active. HTTP 409."""

    def __init__(self, contest_id: Optional[str] = None):
        details = {"contest_id": contest_id} if contest_id else None
        super().__init__(
            code="AUCTION_ALREADY_ACTIVE",
            message="There is already an active auction for this contest",
            status_code=409,
            details=details,
        )


class AuctionNotActiveException(AppException):
    """Raised when a bid is placed on an auction that is not ACTIVE. HTTP 400."""

    def __init__(self, auction_id: Optional[str] = None):
        details = {"auction_id": auction_id} if auction_id else None
        super().__init__(
            code="AUCTION_NOT_ACTIVE",
            message="This auction is not currently active",
            status_code=400,
            details=details,
        )


class InsufficientCurrencyException(AppException):
    """Raised when a team does not have enough currency to place a bid. HTTP 400."""

    def __init__(
        self,
        team_id: Optional[str] = None,
        required: Optional[int] = None,
        available: Optional[int] = None,
    ):
        details: dict = {}
        if team_id:
            details["team_id"] = team_id
        if required is not None:
            details["required"] = required
        if available is not None:
            details["available"] = available
        super().__init__(
            code="INSUFFICIENT_CURRENCY",
            message="Team does not have enough currency to place this bid",
            status_code=400,
            details=details or None,
        )


class BidTooLowException(AppException):
    """Raised when a bid amount is not higher than the current highest bid. HTTP 400."""

    def __init__(
        self,
        bid_amount: Optional[int] = None,
        current_highest: Optional[int] = None,
    ):
        details: dict = {}
        if bid_amount is not None:
            details["bid_amount"] = bid_amount
        if current_highest is not None:
            details["current_highest"] = current_highest
        super().__init__(
            code="BID_TOO_LOW",
            message="Bid amount must be strictly greater than the current highest bid",
            status_code=400,
            details=details or None,
        )


class NotBidderRoleException(AppException):
    """Raised when a user without the BIDDING role tries to place a bid. HTTP 403."""

    def __init__(self, user_id: Optional[str] = None, team_id: Optional[str] = None):
        details: dict = {}
        if user_id:
            details["user_id"] = user_id
        if team_id:
            details["team_id"] = team_id
        super().__init__(
            code="NOT_BIDDER_ROLE",
            message="Only the team member with the BIDDING role can place bids",
            status_code=403,
            details=details or None,
        )


class NoProblemAvailableException(AppException):
    """Raised when there is no next problem to auction in the contest. HTTP 400."""

    def __init__(self, contest_id: Optional[str] = None):
        details = {"contest_id": contest_id} if contest_id else None
        super().__init__(
            code="NO_PROBLEM_AVAILABLE",
            message="No more problems are available for auction in this contest",
            status_code=400,
            details=details,
        )


class TeamNotInContestException(AppException):
    """Raised when a team that is not registered in the contest tries to bid. HTTP 403."""

    def __init__(self, team_id: Optional[str] = None, contest_id: Optional[str] = None):
        details: dict = {}
        if team_id:
            details["team_id"] = team_id
        if contest_id:
            details["contest_id"] = contest_id
        super().__init__(
            code="TEAM_NOT_IN_CONTEST",
            message="This team is not registered in the contest and cannot place bids",
            status_code=403,
            details=details or None,
        )


class AuctionExpiredException(AppException):
    """Raised when a bid is placed after the auction's end_time. HTTP 400."""

    def __init__(self, auction_id: Optional[str] = None):
        details = {"auction_id": auction_id} if auction_id else None
        super().__init__(
            code="AUCTION_ENDED",
            message="This auction has already ended and is no longer accepting bids",
            status_code=400,
            details=details,
        )


class BidRateLimitedException(AppException):
    """Raised when a user places bids faster than the allowed cooldown. HTTP 429."""

    def __init__(self, retry_after_ms: int):
        super().__init__(
            code="BID_RATE_LIMITED",
            message=(
                f"Bidding too fast. Please wait {retry_after_ms} ms before the next bid."
            ),
            status_code=429,
            details={"retry_after_ms": retry_after_ms},
        )
