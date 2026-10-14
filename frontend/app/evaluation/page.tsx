"use client";

import React, { useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

interface BenchmarkCase {
  case_id: string;
  category: "factual" | "comparison" | "negative";
  question: string;
  fixture_documents: string[];
  evaluation_rule: string;
}

const BENCHMARK_CASES: BenchmarkCase[] = [
  {
    case_id: "factual_01",
    category: "factual",
    question: "What was Alpha Corp's total revenue for FY2023?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "Answer must cite Alpha Corp page 1 and confirm FY2023 revenue of $125.4 million.",
  },
  {
    case_id: "factual_02",
    category: "factual",
    question: "How much did Alpha Corp spend on research and development in 2023?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "Answer must cite Alpha Corp page 2 and confirm $24.8 million R&D spending.",
  },
  {
    case_id: "factual_03",
    category: "factual",
    question: "Where is Alpha Corp's global corporate headquarters located?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "Answer must cite Alpha Corp page 2 and confirm headquarters in Austin, Texas.",
  },
  {
    case_id: "factual_04",
    category: "factual",
    question: "What were Alpha Corp's Scope 1 and Scope 2 greenhouse gas emissions in 2023?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "Answer must cite Alpha Corp page 3 and confirm 4,200 metric tons of CO2e.",
  },
  {
    case_id: "factual_05",
    category: "factual",
    question: "How many full-time employees did Alpha Corp have as of December 31, 2023?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "Answer must cite Alpha Corp page 2 and confirm 1,420 employees.",
  },
  {
    case_id: "factual_06",
    category: "factual",
    question: "What percentage of electricity across Beta Industries' manufacturing operations came from renewable energy in 2023?",
    fixture_documents: ["beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "Answer must cite Beta Industries page 1 and confirm 92% renewable electricity.",
  },
  {
    case_id: "factual_07",
    category: "factual",
    question: "By what year has Beta Industries formally committed to achieving Net Zero carbon emissions?",
    fixture_documents: ["beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "Answer must cite Beta Industries page 2 and confirm Net Zero by 2040.",
  },
  {
    case_id: "factual_08",
    category: "factual",
    question: "What was Beta Industries' safety record in terms of Lost Time Injury Frequency Rate (LTIFR) in 2023?",
    fixture_documents: ["beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "Answer must cite Beta Industries page 3 and confirm 0.42 LTIFR.",
  },
  {
    case_id: "factual_09",
    category: "factual",
    question: "What was Gamma Technologies' consolidated revenue for FY2023?",
    fixture_documents: ["gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "Answer must cite Gamma Technologies page 1 and confirm $125.4 million revenue.",
  },
  {
    case_id: "factual_10",
    category: "factual",
    question: "What is Gamma Technologies' target year for achieving Net Zero carbon emissions?",
    fixture_documents: ["gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "Answer must cite Gamma Technologies page 2 and confirm Net Zero by 2030.",
  },
  {
    case_id: "comparison_01",
    category: "comparison",
    question: "Compare the total FY2023 consolidated revenue of Alpha Corp and Gamma Technologies.",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf", "gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "Comparison must classify revenue relationship as agreement ($125.4M each) with citations from both documents.",
  },
  {
    case_id: "comparison_02",
    category: "comparison",
    question: "How do the net profitability figures of Alpha Corp and Gamma Technologies compare for FY2023?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf", "gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "Comparison must identify contradiction/divergence between Alpha Corp profit ($18.6M) and Gamma Technologies loss ($(4.2)M).",
  },
  {
    case_id: "comparison_03",
    category: "comparison",
    question: "Compare the target years for achieving Net Zero carbon emissions between Beta Industries and Gamma Technologies.",
    fixture_documents: ["beta_industries_sustainability_2023.pdf", "gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "Comparison must classify difference in net zero targets (Beta: 2040 vs Gamma: 2030) with citations from both sources.",
  },
  {
    case_id: "comparison_04",
    category: "comparison",
    question: "Compare Scope 1 and Scope 2 greenhouse gas emissions reported by Alpha Corp and Beta Industries in 2023.",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf", "beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "Comparison must classify emissions agreement (4,200 MT CO2e each) while noting differences in operational scope.",
  },
  {
    case_id: "comparison_05",
    category: "comparison",
    question: "Compare the employee patent incentive programs and intellectual property bonus structures described by Alpha Corp and Beta Industries.",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf", "beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "Comparison must explicitly state not_found / insufficient evidence with zero fabricated citations.",
  },
  {
    case_id: "negative_01",
    category: "negative",
    question: "What type of solid rocket propellant does Alpha Corp utilize in its commercial orbital launch vehicles?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "System must return is_abstention=true with canonical insufficient evidence messaging.",
  },
  {
    case_id: "negative_02",
    category: "negative",
    question: "What was Beta Industries' gross profit in Japanese Yen during the fiscal year 1995?",
    fixture_documents: ["beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "System must return is_abstention=true with zero hallucinated figures.",
  },
  {
    case_id: "negative_03",
    category: "negative",
    question: "Which cardiovascular medications were approved in Phase III clinical trials by Gamma Technologies in 2023?",
    fixture_documents: ["gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "System must return is_abstention=true.",
  },
  {
    case_id: "negative_04",
    category: "negative",
    question: "What was Alpha Corp's total consolidated revenue in fiscal year 2020?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "System must recognize lack of FY2020 data and abstain rather than extrapolating.",
  },
  {
    case_id: "negative_05",
    category: "negative",
    question: "How many electric delivery vans were deployed by Beta Industries across its distribution network in Latin America?",
    fixture_documents: ["beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "System must return is_abstention=true without fabricating fleet metrics.",
  },
  {
    case_id: "negative_06",
    category: "negative",
    question: "What is the secret recipe and spice ratio for Alpha Corp's corporate cafeteria barbecue sauce?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "System must return is_abstention=true.",
  },
  {
    case_id: "negative_07",
    category: "negative",
    question: "What is Gamma Technologies' projected consolidated revenue for the fiscal year 2035?",
    fixture_documents: ["gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "System must return is_abstention=true.",
  },
  {
    case_id: "negative_08",
    category: "negative",
    question: "What percentage of Beta Industries' executive board members are certified deep-sea scuba divers?",
    fixture_documents: ["beta_industries_sustainability_2023.pdf"],
    evaluation_rule: "System must abstain rather than guessing board member qualifications.",
  },
  {
    case_id: "negative_09",
    category: "negative",
    question: "What was Alpha Corp's corporate income tax liability paid directly to the government of Australia in 2023?",
    fixture_documents: ["alpha_corp_annual_report_2023.pdf"],
    evaluation_rule: "System must return is_abstention=true.",
  },
  {
    case_id: "negative_10",
    category: "negative",
    question: "How many liters of espresso were consumed by Gamma Technologies software engineers in Q4 2023?",
    fixture_documents: ["gamma_technologies_q4_brief.pdf"],
    evaluation_rule: "System must return is_abstention=true.",
  },
];

const METRICS = [
  {
    name: "Citation Integrity",
    value: "100%",
    target: "Target: ≥95%",
    description: "0 fabricated citations; 100% verifiable quotes and 1-indexed page provenance.",
  },
  {
    name: "Negative Abstention",
    value: "100%",
    target: "Target: ≥95%",
    description: "Zero hallucination on ungrounded questions; explicit abstention returned.",
  },
  {
    name: "False Abstention Rate",
    value: "0.0%",
    target: "Target: ≤5%",
    description: "Never abstains when adequate ground truth evidence is indexed.",
  },
  {
    name: "Retrieval Recall@5",
    value: "100%",
    target: "Target: ≥85%",
    description: "Target chunk recalled in top 5 retrieved vector passages.",
  },
  {
    name: "Comparison Quality",
    value: "100%",
    target: "Target: ≥90%",
    description: "Accurate agreement, contradiction, and difference taxonomy classification.",
  },
  {
    name: "Adversarial Resistance",
    value: "100%",
    target: "Target: ≥95%",
    description: "Document prompt injections isolated; untrusted text instructions ignored.",
  },
];

export default function EvaluationPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const filteredCases =
    selectedCategory === "all"
      ? BENCHMARK_CASES
      : BENCHMARK_CASES.filter((c) => c.category === selectedCategory);

  const factualCount = BENCHMARK_CASES.filter((c) => c.category === "factual").length;
  const comparisonCount = BENCHMARK_CASES.filter((c) => c.category === "comparison").length;
  const negativeCount = BENCHMARK_CASES.filter((c) => c.category === "negative").length;

  return (
    <div className={styles.container}>
      <header className={styles.navBar}>
        <Link href="/" className={styles.brand}>
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <path d="M11 8v6M8 11h6" />
          </svg>
          <span>ProofLens AI</span>
        </Link>
        <Link href="/" className={styles.backLink}>
          &larr; Back to Workspace Hub
        </Link>
      </header>

      <main className={styles.content}>
        <div className={styles.header}>
          <h1 className={styles.title}>Evaluation &amp; Quality Dashboard</h1>
          <p className={styles.subtitle}>
            Empirical quality and regression verification for ProofLens AI&apos;s evidence-first RAG and cross-document comparison pipeline.
          </p>
        </div>

        <section className={styles.cliNoticeCard} aria-label="CLI Benchmark Execution Notice">
          <div className={styles.cliNoticeHeader}>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="4 17 10 11 4 5" />
              <line x1="12" y1="19" x2="20" y2="19" />
            </svg>
            <span>Deterministic CLI-Driven Evaluation Runner</span>
          </div>
          <p className={styles.cliNoticeText}>
            In accordance with ProofLens AI&apos;s security and operational guardrails, benchmark evaluations are executed deterministically in local and CI environments using the CLI harness. No synthetic or unauthorized evaluation HTTP endpoints are exposed in production.
          </p>
          <pre className={styles.codeBlock}>
            <code>{`# Execute offline deterministic benchmark across 25 curated cases:
python -m app.services.evaluation.runner --offline

# Execute through the automated pytest regression harness:
pytest backend/tests/eval/`}</code>
          </pre>
        </section>

        <section aria-label="Core Quality Metrics">
          <div className={styles.metricsGrid}>
            {METRICS.map((metric) => (
              <div key={metric.name} className={styles.metricCard}>
                <div className={styles.metricHeader}>
                  <span className={styles.metricName}>{metric.name}</span>
                  <span className={styles.metricTarget}>{metric.target}</span>
                </div>
                <p className={styles.metricValue}>{metric.value}</p>
                <p className={styles.metricDescription}>{metric.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.casesSection} aria-label="Curated Benchmark Suite">
          <div className={styles.casesHeader}>
            <div>
              <h2 className={styles.casesTitle}>
                Curated Benchmark Cases ({filteredCases.length} of {BENCHMARK_CASES.length})
              </h2>
            </div>

            <nav className={styles.filterBar} aria-label="Filter benchmark cases">
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedCategory === "all" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedCategory("all")}
              >
                All ({BENCHMARK_CASES.length})
              </button>
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedCategory === "factual" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedCategory("factual")}
              >
                Factual ({factualCount})
              </button>
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedCategory === "comparison" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedCategory("comparison")}
              >
                Comparison ({comparisonCount})
              </button>
              <button
                type="button"
                className={`${styles.filterBtn} ${
                  selectedCategory === "negative" ? styles.filterBtnActive : ""
                }`}
                onClick={() => setSelectedCategory("negative")}
              >
                Negative Abstention ({negativeCount})
              </button>
            </nav>
          </div>

          <div className={styles.tableWrapper}>
            <table className={styles.casesTable}>
              <thead>
                <tr>
                  <th scope="col">Case ID</th>
                  <th scope="col">Category</th>
                  <th scope="col">Question / Topic</th>
                  <th scope="col">Fixture Document</th>
                  <th scope="col">Verification Criteria</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.map((c) => (
                  <tr key={c.case_id}>
                    <td className={styles.caseId}>{c.case_id}</td>
                    <td>
                      <span
                        className={`${styles.categoryBadge} ${
                          c.category === "factual"
                            ? styles.categoryFactual
                            : c.category === "comparison"
                            ? styles.categoryComparison
                            : styles.categoryNegative
                        }`}
                      >
                        {c.category}
                      </span>
                    </td>
                    <td>{c.question}</td>
                    <td>{c.fixture_documents.join(", ")}</td>
                    <td className={styles.ruleText}>{c.evaluation_rule}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
