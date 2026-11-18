import type { Team } from './types'

// Use football-data.org IDs to keep the display names independent of upstream spelling.
const chineseTeamNames: Partial<Record<number, string>> = {
  57: '阿森纳',
  58: '阿斯顿维拉',
  61: '切尔西',
  62: '埃弗顿',
  63: '富勒姆',
  64: '利物浦',
  65: '曼城',
  66: '曼联',
  67: '纽卡斯尔联',
  71: '桑德兰',
  73: '热刺',
  322: '赫尔城',
  341: '利兹联',
  349: '伊普斯维奇',
  351: '诺丁汉森林',
  354: '水晶宫',
  397: '布莱顿',
  402: '布伦特福德',
  1044: '伯恩茅斯',
  1076: '考文垂城',
}

export function teamDisplayName(team: Team): string {
  return chineseTeamNames[team.id] ?? team.short_name
}
