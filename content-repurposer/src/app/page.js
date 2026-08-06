"use client";
import { useState, useEffect } from "react";
import "./page.css";

export default function Home() {
  const [content, setContent] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);

  const handleGenerate = () => {
    if (!content.trim()) return;
    setIsProcessing(true);
    setResults(null);

    // Mock AI Processing
    setTimeout(() => {
      setIsProcessing(false);
      setResults({
        twitter: [
          "Thread: Why repurposing content is the ultimate growth hack 🧵👇\\n\\n1. You save hours every week.\\n2. You reach audiences on platforms you otherwise ignore.\\n3. One idea = 10 pieces of content.",
          "Stop creating from scratch every day. The best creators repurpose their hits. #CreatorEconomy"
        ],
        linkedin: [
          "Most creators are on a content treadmill. They create, post, and start over.\\n\\nBut the top 1% do something differently: They repurpose.\\n\\nHere is how you can turn a 20-minute podcast into a week's worth of content:\\n\\n1. Extract 3 main insights.\\n2. Turn each insight into a short text post.\\n3. Take the best text post and expand it into a newsletter.\\n\\nStop working harder. Start working smarter. 💡"
        ],
        instagram: [
          "Are you on the content treadmill? 🏃‍♂️💨\\n\\nIt's time to step off and start REPURPOSING. Your best ideas deserve more than one post. Watch the space for a massive hack on scaling your content. 👇\\n\\n#ContentCreator #MarketingTips #CreatorHacks"
        ],
        newsletter: [
          "Welcome to this week's deep dive. Today we're talking about the 'Content Treadmill'. If you're a creator, you know exactly what I mean. You finish a great piece of content, hit publish, and instantly feel the pressure to start the next one. It's exhausting.\\n\\nThe solution isn't to create more. It's to repurpose better. By taking your core piece of content (like a podcast or a long blog post) and strategically slicing it into micro-content, you can maintain a presence across Twitter, LinkedIn, and Instagram without burning out."
        ]
      });
    }, 2500);
  };

  const clearResults = () => {
    setResults(null);
    setContent("");
  };

  return (
    <main className="app-container">
      <nav className="navbar glass-panel">
        <div className="nav-brand">
          <span className="logo-icon">✨</span>
          <h1 className="logo-text">RePurpose AI</h1>
        </div>
        <div className="nav-links">
          <button className="nav-link active">Dashboard</button>
          <button className="nav-link">Templates</button>
          <button className="nav-link">Settings</button>
        </div>
        <button className="btn btn-primary">Upgrade Pro</button>
      </nav>

      <div className="workspace">
        {!isProcessing && !results && (
          <div className="import-hub glass-panel animate-fade-in">
            <div className="hub-header">
              <h2 className="text-gradient">Turn One Piece Into Ten</h2>
              <p className="text-muted">Paste your blog post, transcript, or ideas below to generate tailored snippets.</p>
            </div>
            
            <div className="input-group">
              <textarea 
                className="content-input" 
                placeholder="Paste your long-form content here..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </div>

            <div className="hub-actions">
              <button 
                className="btn btn-primary generate-btn" 
                onClick={handleGenerate}
                disabled={!content.trim()}
              >
                Generate Magic ✨
              </button>
            </div>
            
            <div className="presets-list">
              <span className="text-muted" style={{fontSize: '0.85rem'}}>Active Presets:</span>
              <span className="preset-tag">Twitter Thread</span>
              <span className="preset-tag">LinkedIn Post</span>
              <span className="preset-tag">Instagram Caption</span>
              <span className="preset-tag">Newsletter Excerpt</span>
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="processing-view flex-center animate-fade-in">
            <div className="loader">
              <div className="spinner"></div>
              <h3 className="text-gradient">AI is analyzing your content...</h3>
              <p className="text-muted">Extracting key insights and crafting platform-specific hooks.</p>
            </div>
          </div>
        )}

        {results && (
          <div className="results-studio animate-fade-in">
            <div className="studio-header flex-between">
              <h2>Your Generated Snippets</h2>
              <button className="btn btn-secondary" onClick={clearResults}>Start Over</button>
            </div>

            <div className="studio-grid">
              <div className="original-pane glass-panel">
                <h3>Original Source</h3>
                <div className="original-content text-muted">
                  {content}
                </div>
              </div>

              <div className="snippets-pane">
                {Object.entries(results).map(([platform, snippets]) => (
                  <div key={platform} className="platform-section glass-panel">
                    <div className="platform-header">
                      <span className={`platform-icon icon-${platform}`}></span>
                      <h3 style={{textTransform: 'capitalize'}}>{platform}</h3>
                    </div>
                    <div className="snippets-list">
                      {snippets.map((snippet, idx) => (
                        <div key={idx} className="snippet-card">
                          <p>{snippet}</p>
                          <div className="snippet-actions">
                            <button className="btn-icon" onClick={() => navigator.clipboard.writeText(snippet)} title="Copy to clipboard">
                              📋 Copy
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
