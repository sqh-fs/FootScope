<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { teamDisplayName } from '../teamNames'
import { matchStatusNames, type Dashboard, type LabMatchStats } from '../types'
import TeamLabel from './TeamLabel.vue'

const props = defineProps<{ dashboard: Dashboard }>()

const metrics = [
  { key: 'xg', label: '预期进球（xG）' },
  { key: 'shots', label: '射门' },
  { key: 'shots_on_target', label: '射正' },
  { key: 'shot_accuracy_pct', label: '射正率' },
  { key: 'half_time_goals', label: '半场进球' },
  { key: 'corners', label: '角球' },
  { key: 'fouls', label: '犯规' },
  { key: 'yellow_cards', label: '黄牌' },
  { key: 'red_cards', label: '红牌' },
]
const kickoffFormat = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23',
})

const season = computed(() => {
  const { start_date, end_date } = props.dashboard.season
  return `${start_date.slice(0, 4)}/${end_date.slice(2, 4)}`
})
const finished = computed(() => props.dashboard.matches.filter((match) => match.status === 'FINISHED'))
const rounds = computed(() => [...new Set(props.dashboard.matches.map((match) => match.matchday))]
  .sort((left, right) => (left ?? Infinity) - (right ?? Infinity)))
const selectedRound = ref<number | null>()
const selectedMatchId = ref<number>()
const roundMatches = computed(() => props.dashboard.matches.filter((match) => match.matchday === selectedRound.value))
const match = computed(() => roundMatches.value.find((entry) => entry.id === selectedMatchId.value))
const details = ref<LabMatchStats>()
const loading = ref(false)
const error = ref(false)
const attempt = ref(0)

watch(rounds, (values) => {
  if (selectedRound.value !== undefined && values.includes(selectedRound.value)) return
  const latest = finished.value.at(-1)
  selectedRound.value = latest ? latest.matchday : values[0]
}, { immediate: true })

watch(roundMatches, (entries) => {
  if (!entries.some((entry) => entry.id === selectedMatchId.value)) selectedMatchId.value = entries[0]?.id
}, { immediate: true })

watch([
  selectedMatchId, () => match.value?.status, () => match.value?.kickoff_utc,
  () => match.value?.home_score, () => match.value?.away_score, attempt,
], async ([id], _, onCleanup) => {
  details.value = undefined
  error.value = false
  loading.value = false
  if (id === undefined) return

  const controller = new AbortController()
  onCleanup(() => controller.abort())
  loading.value = true
  try {
    const response = await fetch(`/api/v1/lab/matches/${id}`, {
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
    })
    if (!response.ok) throw new Error('Match statistics request failed')
    const result = await response.json() as LabMatchStats
    if (!controller.signal.aborted) details.value = result
  } catch {
    if (!controller.signal.aborted) error.value = true
  } finally {
    if (!controller.signal.aborted) loading.value = false
  }
}, { immediate: true })

function metricValue(key: string, side: number) {
  const value = details.value?.stats?.[key]?.[side]
  if (value == null) return '—'
  if (key === 'shot_accuracy_pct') return `${value}%`
  if (key === 'xg') return value.toFixed(2)
  return value
}
</script>

<template>
  <section class="panel" aria-labelledby="season-match-heading">
    <header class="panel-header season-match-heading">
      <div class="panel-title">
        <h2 id="season-match-heading">{{ season }} 英超比赛</h2>
        <span class="subtle-label">{{ finished.length }} / {{ dashboard.matches.length }} 场已结束</span>
      </div>
      <div v-if="rounds.length" class="season-match-controls">
        <select v-model="selectedRound" aria-label="选择英超轮次">
          <option v-for="round in rounds" :key="round ?? 'pending'" :value="round">
            {{ round === null ? '待定轮次' : `第 ${round} 轮` }}
          </option>
        </select>
        <select v-model="selectedMatchId" aria-label="选择英超比赛">
          <option v-for="entry in roundMatches" :key="entry.id" :value="entry.id">
            {{ teamDisplayName(entry.home_team) }} vs {{ teamDisplayName(entry.away_team) }}
          </option>
        </select>
      </div>
    </header>

    <template v-if="match">
      <div class="season-match-score">
        <TeamLabel :team="match.home_team" linked />
        <strong>{{ match.home_score === null || match.away_score === null ? '–' : `${match.home_score} – ${match.away_score}` }}</strong>
        <TeamLabel :team="match.away_team" linked />
        <div class="season-match-meta">
          <time :datetime="match.kickoff_utc">{{ kickoffFormat.format(new Date(match.kickoff_utc)) }}</time>
          <span>{{ matchStatusNames[match.status] ?? '状态待定' }}</span>
        </div>
      </div>

      <p v-if="loading" class="panel-state" role="status">正在读取比赛统计…</p>
      <div v-else-if="error" class="panel-state" role="status">
        暂时无法读取比赛统计。 <button type="button" class="text-button" @click="attempt++">重试</button>
      </div>
      <template v-else-if="details?.stats">
        <table class="season-match-stats">
          <thead><tr><th scope="col">主队</th><th scope="col">比赛统计</th><th scope="col">客队</th></tr></thead>
          <tbody>
            <tr v-for="metric in metrics" :key="metric.key">
              <td>{{ metricValue(metric.key, 0) }}</td>
              <th scope="row">{{ metric.label }}</th>
              <td>{{ metricValue(metric.key, 1) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="season-match-credit">
          逐次射门和传球坐标暂不可用。统计来源 <a :href="details.source_url" target="_blank" rel="noreferrer">Football-Data.co.uk</a>
        </p>
      </template>
      <div v-else-if="details?.status === 'FINISHED'" class="panel-state" role="status">
        这场比赛的统计尚未导入。 <button type="button" class="text-button" @click="attempt++">刷新</button>
      </div>
      <p v-else-if="details?.status === 'AWARDED' || details?.status === 'CANCELLED'" class="panel-state" role="status">这场比赛暂无统计。</p>
      <p v-else class="panel-state" role="status">比赛结束并导入统计后可查看分析。</p>
    </template>
    <p v-else class="panel-state" role="status">暂无赛程，请先同步英超数据。</p>
  </section>
</template>
