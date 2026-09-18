import worker from "./worker.js";

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }
}

function makeRequest(body, options = {}) {
  return new Request(
    "https://orbital-risk-chatbot.example.workers.dev",
    {
      method: options.method || "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: options.origin || "https://likhitha281.github.io",
        "CF-Connecting-IP": options.ip || "203.0.113.10",
      },
      body:
        (options.method || "POST") === "POST"
          ? JSON.stringify(body)
          : undefined,
    }
  );
}

function makeEnv(response = "There are 3 conjunctions in the current dashboard data.") {
  return {
    ALLOWED_ORIGIN: "https://likhitha281.github.io",

    AI: {
      async run(model, input) {
        assert(
          typeof model === "string" && model.length > 0,
          "Worker should provide a model name"
        );

        assert(
          Array.isArray(input.messages),
          "Worker should send messages to Workers AI"
        );

        return {
          response,
        };
      },
    },
  };
}

async function readJson(response) {
  return await response.json();
}

async function run() {
  // ----------------------------------------------------------
  // Valid request
  // ----------------------------------------------------------

  {
    const env = makeEnv(
      "There are 3 conjunctions in the current dashboard data."
    );

    const request = makeRequest({
      question: "How many conjunctions are there?",
      dashboardData: {
        conjunctions: [
          { id: 1 },
          { id: 2 },
          { id: 3 },
        ],
      },
    });

    const response = await worker.fetch(request, env);
    const json = await readJson(response);

    assert(
      response.status === 200,
      "Valid request should return 200"
    );

    assert(
      typeof json.answer === "string",
      "Valid request should return an answer"
    );

    assert(
      json.answer.includes("3 conjunctions"),
      "Answer should pass through the model's text"
    );
  }

  // ----------------------------------------------------------
  // Missing question
  // ----------------------------------------------------------

  {
    const response = await worker.fetch(
      makeRequest({
        dashboardData: {},
      }),
      makeEnv()
    );

    assert(
      response.status === 400,
      "Missing question should return 400"
    );
  }

  // ----------------------------------------------------------
  // Empty question
  // ----------------------------------------------------------

  {
    const response = await worker.fetch(
      makeRequest({
        question: "   ",
        dashboardData: {},
      }),
      makeEnv()
    );

    assert(
      response.status === 400,
      "Empty question should return 400"
    );
  }

  // ----------------------------------------------------------
  // Missing dashboard data
  // ----------------------------------------------------------

  {
    const response = await worker.fetch(
      makeRequest({
        question: "What is the highest risk event?",
      }),
      makeEnv()
    );

    assert(
      response.status === 400,
      "Missing dashboard data should return 400"
    );
  }

  // ----------------------------------------------------------
  // Question too long
  // ----------------------------------------------------------

  {
    const response = await worker.fetch(
      makeRequest({
        question: "x".repeat(501),
        dashboardData: {},
      }),
      makeEnv()
    );

    assert(
      response.status === 400,
      "Question over 500 characters should return 400"
    );
  }

  // ----------------------------------------------------------
  // Missing AI binding
  // ----------------------------------------------------------

  {
    const response = await worker.fetch(
      makeRequest({
        question: "What is the highest priority event?",
        dashboardData: {},
      }),
      {
        ALLOWED_ORIGIN:
          "https://likhitha281.github.io",
      }
    );

    assert(
      response.status === 500,
      "Missing AI binding should return 500"
    );
  }

  // ----------------------------------------------------------
  // AI failure
  // ----------------------------------------------------------

  {
    const env = {
      ALLOWED_ORIGIN:
        "https://likhitha281.github.io",

      AI: {
        async run() {
          throw new Error("Simulated Workers AI failure");
        },
      },
    };

    const response = await worker.fetch(
      makeRequest({
        question: "What is the highest priority event?",
        dashboardData: {},
      }),
      env
    );

    assert(
      response.status === 503,
      "Workers AI failure should return 503"
    );
  }

  // ----------------------------------------------------------
  // Invalid origin
  // ----------------------------------------------------------

  {
    const response = await worker.fetch(
      makeRequest(
        {
          question: "Hello",
          dashboardData: {},
        },
        {
          origin: "https://example.com",
        }
      ),
      makeEnv()
    );

    assert(
      response.status === 403,
      "Unexpected origin should return 403"
    );
  }

  // ----------------------------------------------------------
  // OPTIONS preflight
  // ----------------------------------------------------------

  {
    const request = new Request(
      "https://orbital-risk-chatbot.example.workers.dev",
      {
        method: "OPTIONS",
        headers: {
          Origin:
            "https://likhitha281.github.io",
        },
      }
    );

    const response = await worker.fetch(
      request,
      makeEnv()
    );

    assert(
      response.status === 204,
      "OPTIONS should return 204"
    );

    assert(
      response.headers.get(
        "Access-Control-Allow-Origin"
      ) === "https://likhitha281.github.io",
      "OPTIONS should include the allowed CORS origin"
    );
  }

  // ----------------------------------------------------------
  // Non-POST method
  // ----------------------------------------------------------

  {
    const request = new Request(
      "https://orbital-risk-chatbot.example.workers.dev",
      {
        method: "GET",
        headers: {
          Origin:
            "https://likhitha281.github.io",
        },
      }
    );

    const response = await worker.fetch(
      request,
      makeEnv()
    );

    assert(
      response.status === 405,
      "GET should return 405"
    );
  }

  console.log("PASS: chatbot worker tests");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});