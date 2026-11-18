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

export function isComplete(match: Match) {
  return match.status === 'FINISHED' || match.status === 'AWARDED'
}
