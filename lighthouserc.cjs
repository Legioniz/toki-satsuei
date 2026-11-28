module.exports = {
  ci: {
    collect: {
      url: [
        "https://127.0.0.1:8443/",
        "https://127.0.0.1:8443/booking.html",
        "https://127.0.0.1:8443/library.html",
        "https://127.0.0.1:8443/policies.html",
        "https://127.0.0.1:8443/admin.html",
        "https://127.0.0.1:8443/client-gallery.html",
        "https://127.0.0.1:8443/404.html"
      ],
      startServerCommand: "python scripts/qa_support/toki_lighthouse_https_server.py",
      startServerReadyPattern: "TOKI_LHCI_SERVER_READY",
      numberOfRuns: 1,
      chromePath: process.env.CHROME_PATH,
      settings: {
        preset: "mobile",
        chromeFlags: ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"]
      }
    },
    assert: {
      assertions: {
        "categories:performance": ["warn", { minScore: 0.50 }],
        "categories:accessibility": ["warn", { minScore: 0.90 }],
        "categories:best-practices": ["warn", { minScore: 0.90 }],
        "categories:seo": ["warn", { minScore: 0.90 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 5000 }],
        "cumulative-layout-shift": ["warn", { maxNumericValue: 0.15 }],
        "total-blocking-time": ["warn", { maxNumericValue: 600 }]
      }
    },
    upload: {
      target: "filesystem",
      outputDir: "lighthouseci-reports"
    }
  }
};
