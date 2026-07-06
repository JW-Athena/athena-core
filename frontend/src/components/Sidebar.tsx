export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">A</div>
        <div>
          <h1>ATHENA</h1>
          <p>Executive OS</p>
        </div>
      </div>

      <nav className="nav">
        <button className="nav-item active">Command</button>
        <button className="nav-item">AI</button>
        <button className="nav-item">Documents</button>
        <button className="nav-item">Knowledge</button>
        <button className="nav-item">Products</button>
        <button className="nav-item">Tenders</button>
        <button className="nav-item">Settings</button>
      </nav>
    </aside>
  );
}