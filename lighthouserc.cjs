module.exports = {
  ci: {
    collect: {
      staticDistDir: "./dist",
      url: [
        "http://localhost/",
        "http://localhost/booking.html",
        "http://localhost/library.html",
        "http://localhost/policies.html",
        "http://localhost/admin.html",
        "http://localhost/client-gallery.html",
        "http://localhost/404.html"
      ],
      numberOfRuns: 1,
      chromePath: process.env.CHROME_PATH,
      settings: {
        preset: "mobile",
        chromeFlags: ["--no-sandbox", "--disable-dev-shm-usage"]
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
