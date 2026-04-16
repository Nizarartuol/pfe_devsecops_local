import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
    stages: [
        { duration: '2m', target: 1000 },
        { duration: '5m', target: 1000 },
        { duration: '2m', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'],
        http_req_failed: ['rate<0.1'],
    },
    tags: { workload: '1000users' },
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