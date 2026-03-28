"""Bidding Handler Layer — parse requests and format HTTP responses only."""

import logging

from fastapi import Body, Depends, Path

from app.api.auth.dependencies import get_current_user
from app.api.auth.schemas import UserWithPermissions
from app.api.bidding.schemas.bidding import (
    AuctionListResponse,
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
    logger.info(
        f"[START_AUCTION] Requested by user={current_user.user_id} | "
        f"contest={contest_id} | "
        f"problem={request.data.contest_problem_id!r} | "
        f"duration={request.data.duration_seconds}s"
    )

    auction = await bidding_service.start_auction(
        contest_id=contest_id,
        contest_problem_id=request.data.contest_problem_id,
        duration_seconds=request.data.duration_seconds,
        requesting_user_id=current_user.user_id,
    )

    logger.info(
        f"[START_AUCTION] Success — auction={auction.id} | "
        f"contest_problem={auction.contest_problem_id} | "
        f"base_price={auction.base_price} | "
        f"end_time={auction.end_time}"
    )
    return AuctionResponse(data=AuctionResponseData.model_validate(auction))


async def get_all_auctions_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionListResponse:
    """
    Return all auctions for a contest, ordered by created_at ascending.
    """
    logger.debug(
        f"[GET_ALL_AUCTIONS] user={current_user.user_id} | contest={contest_id}"
    )

    auctions = await bidding_service.get_all_auctions(
        contest_id=contest_id,
        requesting_user_id=current_user.user_id,
    )

    logger.debug(
        f"[GET_ALL_AUCTIONS] Returning {len(auctions)} auctions for contest={contest_id}"
    )
    return AuctionListResponse(
        data=[AuctionResponseData.model_validate(a) for a in auctions]
    )


async def get_current_auction_handler(
    contest_id: str = Path(..., description="Contest ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionResponse:
    """
    Return the current (or most recent) auction for a contest.
    """
    logger.debug(
        f"[GET_CURRENT_AUCTION] user={current_user.user_id} | contest={contest_id}"
    )

    auction = await bidding_service.get_current_auction(contest_id=contest_id)

    logger.debug(
        f"[GET_CURRENT_AUCTION] Returning auction={auction.id} | status={auction.status.value}"
    )
    return AuctionResponse(data=AuctionResponseData.model_validate(auction))


async def get_auction_result_handler(
    auction_id: str = Path(..., description="Auction ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionResultResponse:
    """
    Return the final result of an auction (winning team and bid amount).
    """
    logger.debug(
        f"[GET_AUCTION_RESULT] user={current_user.user_id} | auction={auction_id}"
    )

    auction = await bidding_service.get_auction_result(auction_id=auction_id)

    logger.info(
        f"[GET_AUCTION_RESULT] auction={auction.id} | status={auction.status.value} | "
        f"winner={auction.winning_team_id!r} | winning_bid={auction.winning_bid!r}"
    )
    return AuctionResultResponse(
        data=AuctionResultData(
            auction_id=auction.id,
            contest_problem_id=auction.contest_problem_id,
            winning_team_id=auction.winning_team_id,
            winning_bid=auction.winning_bid,
            status=auction.status,
        )
    )


async def force_end_auction_handler(
    auction_id: str = Path(..., description="Auction ID"),
    current_user: UserWithPermissions = Depends(get_current_user),
    bidding_service: BiddingService = Depends(get_bidding_service),
) -> AuctionResponse:
    """
    Force-end an active auction immediately. Organizer of the contest only.
    """
    logger.info(
        f"[FORCE_END_AUCTION] Requested by user={current_user.user_id} | auction={auction_id}"
    )

    auction = await bidding_service.force_end_auction(
        auction_id=auction_id,
        requesting_user_id=current_user.user_id,
    )

    logger.info(
        f"[FORCE_END_AUCTION] Success — auction={auction.id} | "
        f"winner={auction.winning_team_id!r} | winning_bid={auction.winning_bid!r}"
    )
    return AuctionResponse(data=AuctionResponseData.model_validate(auction))
