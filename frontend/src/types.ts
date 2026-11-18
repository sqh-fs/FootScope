export interface Team {
  id: number
  name: string
  short_name: string
  code: string
}

export interface Standing {
  team: Team
  position: number
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
}

export interface Match {
  id: number
  matchday: number | null
  kickoff_utc: string
  status: string
  home_team: Team
  away_team: Team
  home_score: number | null
  away_score: number | null
}

export interface Dashboard {
  season: { start_date: string; end_date: string; current_matchday: number | null }
  standings: Standing[]
  matches: Match[]
  meta: { source: string; last_synced_at: string; is_stale: boolean }
}

export interface SquadPlayer {
  id: number
  name: string
  position: string | null
  nationality: string | null
}

export interface TeamProfile {
  team: Team
  season: { start_date: string; end_date: string }
  roster: { players: SquadPlayer[]; coach: string | null; venue: string | null } | null
  meta: { source: string; last_synced_at: string | null }
}

export interface LabPlayer {
  id: number
  name: string
  number: number
  position: string | null
  started: boolean
  appeared: boolean
}

export interface LabTeam {
  id: number
  name: string
  score: number
  formation: string
  players: LabPlayer[]
}

export interface Shot {
  id: string
  team_id: number
  player: string
  x: number
  y: number
  xg: number | null
  minute: number
  second: number
  period: number
  outcome: string
}

export interface LabMatch {
  id: number
  date: string
  venue: string | null
  teams: [LabTeam, LabTeam]
  shootout: [number, number]
  shots: Shot[]
  source_url: string
}

export function isComplete(match: Match) {
  return match.status === 'FINISHED' || match.status === 'AWARDED'
}
