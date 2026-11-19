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

export interface LabMatchStats {
  status: string
  stats: Record<string, [number | null, number | null]> | null
  source_url: string
}

export const matchStatusNames: Record<string, string> = {
  SCHEDULED: '待开赛',
  TIMED: '待开赛',
  IN_PLAY: '进行中',
  PAUSED: '中场休息',
  FINISHED: '已结束',
  AWARDED: '已判定',
  POSTPONED: '延期',
  SUSPENDED: '暂停',
  CANCELLED: '取消',
}

export function isComplete(match: Match) {
  return match.status === 'FINISHED' || match.status === 'AWARDED'
}
