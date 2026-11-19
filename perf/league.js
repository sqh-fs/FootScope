import { check, sleep } from 'k6'
import execution from 'k6/execution'
import http from 'k6/http'

const base = __ENV.BASE_URL || 'http://127.0.0.1:8010'
const competition = '/api/v1/competitions/PL'
const models = {
  light: { visible: 0.4, extra: 0.2 },
  medium: { visible: 0.8, extra: 1 },
  high: { visible: 1, extra: 5 },
}
const model = models[__ENV.MODEL || 'medium']
if (!model) throw new Error('MODEL must be light, medium or high')

const online = Number(__ENV.ONLINE || 100)
const requestsPerMinute = model.visible + model.extra
const rate = Number(__ENV.RPS || Math.max(1, Math.round(online * requestsPerMinute / 60)))
const duration = __ENV.DURATION || '15m'
const headers = __ENV.ACCEPT_ENCODING ? { 'Accept-Encoding': __ENV.ACCEPT_ENCODING } : {}
const estimatedVUs = Math.max(10, Math.ceil(rate * 0.25))
const arrival = {
  executor: 'constant-arrival-rate',
  rate,
  timeUnit: '1s',
  duration,
  preAllocatedVUs: estimatedVUs,
  maxVUs: Math.max(estimatedVUs, rate),
}
const sessions = {
  executor: 'ramping-vus',
  startVUs: 0,
  stages: [
    { duration: '5m', target: online },
    { duration, target: online },
    { duration: '2m', target: 0 },
  ],
}

export const options = {
  scenarios: { league: __ENV.MODE === 'sessions' ? sessions : arrival },
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
  thresholds: {
    http_req_failed: ['rate<0.001'],
    checks: ['rate>0.999'],
    dropped_iterations: ['count==0'],
    'http_req_duration{name:competition}': ['avg<=100', 'p(95)<=250', 'p(99)<=500'],
    'http_req_duration{name:team}': ['avg<=80', 'p(95)<=200', 'p(99)<=400'],
    'http_req_duration{name:match}': ['avg<=80', 'p(95)<=200', 'p(99)<=400'],
  },
}

export function setup() {
  const response = http.get(base + competition, { responseType: 'text', timeout: '5s' })
  if (response.status !== 200) throw new Error('Load a league snapshot before running the benchmark')
  const league = response.json()
  const teams = league.standings.map(({ team }) => team.id)
  const finished = league.matches.filter(match => match.status === 'FINISHED').map(match => match.id)
  const upcoming = league.matches.filter(match => match.status !== 'FINISHED').map(match => match.id)
  if (!teams.length || !finished.length || !upcoming.length) {
    throw new Error('The benchmark fixture needs teams and both finished and upcoming matches')
  }
  return { teams, finished, upcoming }
}

export default function ({ teams, finished, upcoming }) {
  const iteration = execution.scenario.iterationInTest
  const fraction = ((iteration * 37) % 100) / 100
  const competitionThreshold = (model.visible + model.extra * 0.2) / requestsPerMinute
  const teamThreshold = competitionThreshold + model.extra * 0.2 / requestsPerMinute
  let path = competition
  let name = 'competition'
  if (fraction >= teamThreshold) {
    const matches = iteration % 2 === 0 ? finished : upcoming
    path = '/api/v1/lab/matches/' + matches[iteration % matches.length]
    name = 'match'
  } else if (fraction >= competitionThreshold) {
    path = '/api/v1/teams/' + teams[iteration % teams.length]
    name = 'team'
  }
  const response = http.get(base + path, { headers, tags: { name }, timeout: '5s' })
  check(response, { 'HTTP 200': result => result.status === 200 })
  if (__ENV.MODE === 'sessions') sleep((0.5 + Math.random()) * 60 / requestsPerMinute)
}
