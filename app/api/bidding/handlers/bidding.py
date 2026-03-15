"""Bidding Handler Layer — parse requests and format HTTP responses only."""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.bidding.schemas.bidding import (
    AuctionResponse,
    AuctionResponseData,
    AuctionResultData,
    AuctionResultResponse,
    StartAuctionRequest,
)
from app.api.bidding.services.bidding import BiddingService, get_bidding_service

logger = logging.getLogger(__name__)


async def start_auction_handler(
    contest_id: str = Path(..., description="Contest ID"),
    request: StartAuctionRequest = Body(...),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionResponse:
    """
    Start the next auction for a contest.

    The contest must be ACTIVE and no other auction may be running.
    Returns the newly created auction object.
    """
    auction = await bidding_service.start_auction(
        contest_id=contest_id,
        contest_problem_id=request.data.contest_problem_id,
        duration_seconds=request.data.duration_seconds,
        requesting_user_id=current_user.user_id,
    )
    logger.info(
        f"Auction {auction.id} started by user {current_user.user_id} "
        f"in contest {contest_id}"
    )
    return AuctionResponse(data=AuctionResponseData.model_validate(auction))


async def get_current_auction_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionResponse:
    """
    Return the current (or most recent) auction for a contest.
    """
    auction = await bidding_service.get_current_auction(contest_id=contest_id)
    return AuctionResponse(data=AuctionResponseData.model_validate(auction))


async def get_auction_result_handler(
    auction_id: str = Path(..., description="Auction ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionResultResponse:
    """
    Return the final result of an auction (winning team and bid amount).
    """
    auction = await bidding_service.get_auction_result(auction_id=auction_id)
    return AuctionResultResponse(
        data=AuctionResultData(
            auction_id=auction.id,
            contest_problem_id=auction.contest_problem_id,
            winning_team_id=auction.winning_team_id,
            winning_bid=auction.winning_bid,
            status=auction.status,
        )
    )
