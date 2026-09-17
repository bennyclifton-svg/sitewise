from app.agent.turn_journal import PostgresTurnJournal
from app.agent.turn_supervisor import TurnSupervisor

# Explicit registry shared by the single API process and its lifespan.
agent_turn_supervisor = TurnSupervisor(PostgresTurnJournal())
