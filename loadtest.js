import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
    stages: [
        { duration: '2m', target: 50 },   // montée progressive à 50 users
        { duration: '5m', target: 100 },  // charge maximale 100 users
        { duration: '2m', target: 0 },    // descente progressive
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'], // 95% des requêtes sous 2s
        http_req_failed: ['rate<0.1'],     // moins de 10% d'erreurs
    },
};

export default function () {
    const BASE_URL = 'http://localhost:18080';

    // Test page principale
    let res = http.get(`${BASE_URL}/`);
    check(res, {
        'homepage status 200': (r) => r.status === 200,
    });

    sleep(1);

    // Test page produits
    res = http.get(`${BASE_URL}/product/OLJCESPC7Z`);
    check(res, {
        'product page status 200': (r) => r.status === 200,
    });

    sleep(1);
}