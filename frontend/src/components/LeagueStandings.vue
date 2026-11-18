<script setup lang="ts">
import { ListOrdered } from '@lucide/vue'
import TeamLabel from './TeamLabel.vue'
import type { Standing } from '../types'

defineProps<{ standings: Standing[] }>()
</script>

<template>
  <section id="standings" class="panel" aria-labelledby="standings-heading">
    <header class="panel-header">
      <div class="panel-title">
        <span class="section-icon"><ListOrdered :size="18" /></span>
        <h2 id="standings-heading">积分榜</h2>
      </div>
      <span class="subtle-label">{{ standings.length }} 支球队</span>
    </header>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col" class="rank-cell" title="排名">#</th>
            <th scope="col" class="name-cell">球队</th>
            <th scope="col" title="已赛场次">场</th>
            <th scope="col" class="record-cell" title="胜场">胜</th>
            <th scope="col" class="record-cell" title="平局">平</th>
            <th scope="col" class="record-cell" title="负场">负</th>
            <th scope="col" class="goals-cell">进球</th>
            <th scope="col" class="goals-cell">失球</th>
            <th scope="col">净胜</th>
            <th scope="col" class="points-cell">积分</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in standings" :key="row.team.id">
            <td class="rank-cell"><span :class="{ 'leader-rank': row.position === 1 }">{{ row.position }}</span></td>
            <th scope="row" class="name-cell"><TeamLabel :team="row.team" linked /></th>
            <td>{{ row.played }}</td>
            <td class="record-cell">{{ row.won }}</td>
            <td class="record-cell">{{ row.drawn }}</td>
            <td class="record-cell">{{ row.lost }}</td>
            <td class="goals-cell">{{ row.goals_for }}</td>
            <td class="goals-cell">{{ row.goals_against }}</td>
            <td>{{ row.goal_difference > 0 ? '+' : '' }}{{ row.goal_difference }}</td>
            <td class="points-cell">{{ row.points }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
