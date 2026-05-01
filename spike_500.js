import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
    stages: [
        { duration: '30s', target: 10 },   // base normale
        { duration: '30s', target: 500 },  // spike brutal
        { duration: '3m',  target: 500 },  // maintien du spike
        { duration: '1m',  target: 10 },   // retour normal
        { duration: '1m',  target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<3000'],
        http_req_failed: ['rate<0.2'],
    },
    tags: { workload: 'spike_500' },
};

export default function () {
    const BASE_URL = 'http://localhost:18080';
    let res = http.get(`${BASE_URL}/`);
    check(res, { 'homepage 200': (r) => r.status === 200 });
    sleep(1);
    res = http.get(`${BASE_URL}/product/OLJCESPC7Z`);
    check(res, { 'product 200': (r) => r.status === 200 });
    sleep(1);
}