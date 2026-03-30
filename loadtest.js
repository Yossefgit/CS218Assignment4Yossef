import http from "k6/http";
import { sleep } from "k6";

export const options = {
  vus: 10,
  duration: "30s",
};

export default function () {
  const payload = JSON.stringify({
    name: "test",
    value: 100,
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  http.post("http://localhost:8080/items", payload, params);
  http.get("http://localhost:8080/health");

  sleep(1);
}