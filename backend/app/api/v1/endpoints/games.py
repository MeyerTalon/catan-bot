"""Game endpoints: lobbies, seating, starting, and playing moves."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.game import GameActionRequest, GameCreate, GameDetail, GameList
from app.services.game_service import game_service

router = APIRouter()


@router.get('', response_model=GameList)
def list_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameList:
    """List the user's games and open lobbies they could join.

    Args:
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The user's games and joinable lobbies.
    """
    return game_service.list_games(db, current_user)


@router.post('', response_model=GameDetail, status_code=status.HTTP_201_CREATED)
def create_game(
    payload: GameCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Open a lobby hosted by the user, optionally with bots already seated.

    Args:
        payload: Table size and bot count.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The new lobby.
    """
    return game_service.create_game(db, current_user, payload)


@router.get('/{game_id}', response_model=GameDetail)
def get_game(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Get a game and the user's view of the board. Clients poll this.

    Args:
        game_id: Game id.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The game; spectators see no private hands.

    Raises:
        HTTPException: 404 if the game does not exist.
    """
    return game_service.get_game(db, current_user, game_id)


@router.post('/{game_id}/join', response_model=GameDetail)
def join_game(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Take a free seat in a lobby.

    Args:
        game_id: Game id.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The lobby.

    Raises:
        HTTPException: 404 if missing; 409 if started or full.
    """
    return game_service.join_game(db, current_user, game_id)


@router.post('/{game_id}/leave', status_code=status.HTTP_204_NO_CONTENT)
def leave_game(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Leave a game: frees a lobby seat (the host closes the lobby) or hands
    a seat in a running game to a bot.

    Args:
        game_id: Game id.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        Empty 204 response.

    Raises:
        HTTPException: 404 if missing or not seated.
    """
    game_service.leave_game(db, current_user, game_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/{game_id}/bots', response_model=GameDetail)
def add_bot(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Seat a random bot (host only).

    Args:
        game_id: Game id.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The lobby.

    Raises:
        HTTPException: 403 if not the host; 404 if missing; 409 if started or full.
    """
    return game_service.add_bot(db, current_user, game_id)


@router.delete('/{game_id}/seats/{seat}', response_model=GameDetail)
def remove_seat(
    game_id: int,
    seat: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Remove a bot or another player from the lobby (host only).

    Args:
        game_id: Game id.
        seat: Seat to clear.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The lobby.

    Raises:
        HTTPException: 403 if not the host; 404 if missing or empty; 409 if started.
    """
    return game_service.remove_seat(db, current_user, game_id, seat)


@router.post('/{game_id}/start', response_model=GameDetail)
def start_game(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Start the game with whoever is seated (host only, two or more players).

    Args:
        game_id: Game id.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The started game.

    Raises:
        HTTPException: 403 if not the host; 404 if missing; 409 if started or too few players.
    """
    return game_service.start_game(db, current_user, game_id)


@router.post('/{game_id}/actions', response_model=GameDetail)
def submit_action(
    game_id: int,
    payload: GameActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetail:
    """Make a move; bots then play until a human is up.

    Args:
        game_id: Game id.
        payload: The move.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        The game after the move and any bot moves.

    Raises:
        HTTPException: 400 if the move is illegal; 403 if not seated; 404 if
            missing; 409 if the game is not in progress.
    """
    return game_service.submit_action(db, current_user, game_id, payload.action)
