<script setup lang="ts">
import { CircleAlert, Crosshair, Users } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import type { LabMatch, LabTeam, Shot } from '../types'

const teamNames: Partial<Record<number, string>> = { 779: '阿根廷', 771: '法国' }
const logoUrl = '/api/v1/lab/statsbomb-logo.png'
const outcomes: Record<string, string> = {
  Goal: '进球', Saved: '被扑救', Blocked: '被封堵', 'Off T': '射偏',
  Wayward: '偏出', Post: '击中门框', 'Saved To Post': '扑救后击中门框', 'Saved Off Target': '扑出场外',
}
const positions: Record<string, string> = {
  Goalkeeper: '门将', 'Right Back': '右后卫', 'Left Back': '左后卫',
  'Right Center Back': '右中卫', 'Left Center Back': '左中卫', 'Center Back': '中后卫',
  'Right Wing Back': '右翼卫', 'Left Wing Back': '左翼卫',
  'Center Defensive Midfield': '后腰', 'Right Defensive Midfield': '右后腰', 'Left Defensive Midfield': '左后腰',
  'Right Center Midfield': '右中场', 'Center Midfield': '中场', 'Left Center Midfield': '左中场',
  'Right Midfield': '右边前卫', 'Left Midfield': '左边前卫',
  'Center Attacking Midfield': '前腰', 'Right Attacking Midfield': '右前腰', 'Left Attacking Midfield': '左前腰',
  'Right Wing': '右边锋', 'Left Wing': '左边锋', 'Center Forward': '中锋',
  'Right Center Forward': '右中锋', 'Left Center Forward': '左中锋', 'Secondary Striker': '影锋',
}

const match = ref<LabMatch>()
const loading = ref(true)
const error = ref('')
const filterTeamId = ref<number | null>(null)
const selectedShotId = ref('')
const visibleShots = computed(() => match.value?.shots.filter((shot) =>
  filterTeamId.value === null || filterTeamId.value === shot.team_id,
) ?? [])
const selectedShot = computed(() => visibleShots.value.find((shot) => shot.id === selectedShotId.value))
const rosterTeam = computed(() => match.value?.teams.find((team) => team.id === filterTeamId.value) ?? match.value?.teams[0])
const rosterGroups = computed(() => {
  const players = rosterTeam.value?.players ?? []
  return [
    { label: '首发 11 人', players: players.filter((player) => player.started) },
    { label: '其他比赛名单球员', players: players.filter((player) => !player.started) },
  ]
})
const selectedXg = computed(() => {
  const values = visibleShots.value.flatMap((shot) => shot.xg === null ? [] : [shot.xg])
  return values.length ? values.reduce((sum, part) => sum + part, 0).toFixed(2) : '—'
})
const selectedGoals = computed(() => visibleShots.value.filter((shot) => shot.outcome === 'Goal').length)

function labelFor(team: LabTeam) {
  return teamNames[team.id] ?? team.name
}

function shotLabel(shot: Shot) {
  return `${shot.minute}:${String(shot.second).padStart(2, '0')} ${shot.player} · ${outcomes[shot.outcome] ?? shot.outcome}`
}

function selectTeam(id: number | null) {
  filterTeamId.value = id
  selectedShotId.value = ''
}

async function loadMatch() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/v1/lab/world-cup-final', { signal: AbortSignal.timeout(10000) })
    if (response.status === 503) {
      error.value = '尚未导入世界杯决赛样本。'
      return
    }
    if (!response.ok) throw new Error('Lab request failed')
    match.value = await response.json() as LabMatch
  } catch {
    error.value = '暂时无法读取历史比赛。'
  } finally {
    loading.value = false
  }
}

onMounted(loadMatch)
</script>

<template>
  <p v-if="loading" class="panel panel-state" role="status">正在读取历史比赛…</p>
  <div v-else-if="error" class="notice" role="status">
    <CircleAlert :size="17" /> {{ error }} <button class="text-button" type="button" @click="loadMatch">重试</button>
  </div>
  <template v-else-if="match">
    <section class="panel historical-banner" aria-labelledby="historical-match-title">
      <div class="historical-stage">
        <h2 id="historical-match-title">2022 世界杯决赛</h2>
        <span>{{ match.date }}<template v-if="match.venue"> · {{ match.venue }}</template></span>
      </div>
      <div class="match-scoreboard">
        <button class="match-team home-team" type="button" :aria-pressed="filterTeamId === match.teams[0].id" @click="selectTeam(match.teams[0].id)">
          <span class="team-color" aria-hidden="true"></span>{{ labelFor(match.teams[0]) }}
        </button>
        <div class="historical-score">
          <strong>{{ match.teams[0].score }} – {{ match.teams[1].score }}</strong>
          <small>点球大战 {{ match.shootout[0] }} : {{ match.shootout[1] }}</small>
        </div>
        <button class="match-team away-team" type="button" :aria-pressed="filterTeamId === match.teams[1].id" @click="selectTeam(match.teams[1].id)">
          <span class="team-color" aria-hidden="true"></span>{{ labelFor(match.teams[1]) }}
        </button>
      </div>
    </section>

    <div class="shot-dashboard">
      <section class="panel shot-panel" aria-labelledby="shot-heading">
        <header class="panel-header shot-header">
          <div class="panel-title">
            <span class="section-icon"><Crosshair :size="17" /></span>
            <h2 id="shot-heading">射门分布</h2>
          </div>
          <div class="shot-filters" aria-label="射门球队筛选">
            <button type="button" :aria-pressed="filterTeamId === null" @click="selectTeam(null)">全部</button>
            <button v-for="team in match.teams" :key="team.id" type="button"
              :aria-pressed="filterTeamId === team.id" @click="selectTeam(team.id)">{{ labelFor(team) }}</button>
          </div>
        </header>
        <div class="shot-field-wrap">
          <div class="shot-field" aria-label="射门位置图">
            <svg viewBox="0 0 120 80" preserveAspectRatio="none" aria-hidden="true">
              <path d="M 0.35 0.35 H 119.65 V 79.65 H 0.35 Z M 60 0 V 80 M 0 18 H 18 V 62 H 0 M 120 18 H 102 V 62 H 120 M 0 30 H 6 V 50 H 0 M 120 30 H 114 V 50 H 120 M 18 32 A 10 10 0 0 1 18 48 M 102 32 A 10 10 0 0 0 102 48" />
              <circle cx="60" cy="40" r="10" />
              <circle class="pitch-spot" cx="60" cy="40" r=".55" />
              <circle class="pitch-spot" cx="12" cy="40" r=".55" />
              <circle class="pitch-spot" cx="108" cy="40" r=".55" />
            </svg>
            <button v-for="shot in visibleShots" :key="shot.id" type="button" class="shot-marker"
              :class="{ 'away-shot': shot.team_id === match.teams[1].id, 'goal-shot': shot.outcome === 'Goal' }"
              :style="{ left: `${shot.x / 1.2}%`, top: `${shot.y / 0.8}%`, '--shot-size': `${10 + Math.sqrt(shot.xg ?? 0) * 17}px` }"
              :aria-label="shotLabel(shot)" :aria-pressed="selectedShotId === shot.id"
              @click="selectedShotId = shot.id"></button>
          </div>
          <div class="pitch-legend"><span>实心点表示进球 · 点越大 xG 越高</span><span>进攻方向 →</span></div>
        </div>
      </section>
      <section class="panel shot-summary" aria-labelledby="shot-detail-heading">
        <header class="panel-header"><h2 id="shot-detail-heading">射门详情</h2></header>
        <dl class="shot-totals">
          <div><dt>射门</dt><dd>{{ visibleShots.length }}</dd></div>
          <div><dt>进球</dt><dd>{{ selectedGoals }}</dd></div>
          <div><dt>总 xG</dt><dd>{{ selectedXg }}</dd></div>
        </dl>
        <div class="shot-detail">
          <label for="select-shot">选择射门</label>
          <select id="select-shot" v-model="selectedShotId">
            <option value="">按时间查看</option>
            <option v-for="shot in visibleShots" :key="shot.id" :value="shot.id">{{ shotLabel(shot) }}</option>
          </select>
          <dl v-if="selectedShot" class="shot-facts" aria-live="polite">
            <div><dt>球员</dt><dd>{{ selectedShot.player }}</dd></div>
            <div><dt>时间</dt><dd>{{ selectedShot.minute }}:{{ String(selectedShot.second).padStart(2, '0') }}<template v-if="selectedShot.period > 2"> · 加时</template></dd></div>
            <div><dt>结果</dt><dd>{{ outcomes[selectedShot.outcome] ?? selectedShot.outcome }}</dd></div>
            <div><dt>xG</dt><dd>{{ selectedShot.xg?.toFixed(2) ?? '—' }}</dd></div>
          </dl>
          <p v-else>点击球场上的射门点查看详情。</p>
        </div>
        <p class="shot-scope">射门和 xG 统计覆盖常规时间与加时。</p>
      </section>
    </div>

    <section v-if="rosterTeam" class="panel historic-roster" aria-labelledby="historic-roster-heading">
      <header class="panel-header shot-header">
        <div class="panel-title">
          <span class="section-icon"><Users :size="17" /></span>
          <h2 id="historic-roster-heading">{{ labelFor(rosterTeam) }}比赛阵容</h2>
        </div>
        <div class="shot-filters" aria-label="选择阵容球队">
          <button v-for="team in match.teams" :key="team.id" type="button"
            :aria-pressed="rosterTeam.id === team.id" @click="selectTeam(team.id)">{{ labelFor(team) }}</button>
        </div>
      </header>
      <p class="formation">开场阵型 <strong>{{ rosterTeam.formation }}</strong></p>
      <div class="historic-roster-grid">
        <section v-for="group in rosterGroups" :key="group.label" class="roster-group historic-group">
          <h3>{{ group.label }}</h3>
          <ul class="historic-players">
            <li v-for="player in group.players" :key="player.id">
              <span class="shirt-number">{{ player.number }}</span>
              <strong>{{ player.name }}</strong>
              <small v-if="player.position" :title="player.position">{{ positions[player.position] ?? player.position }}</small>
              <small v-else-if="!player.appeared">未出场</small>
            </li>
          </ul>
        </section>
      </div>
    </section>

    <a class="statsbomb-credit" :href="match.source_url" target="_blank" rel="noreferrer">
      <span>比赛数据来自 StatsBomb Open Data</span>
      <img :src="logoUrl" alt="StatsBomb" />
    </a>
  </template>
</template>
