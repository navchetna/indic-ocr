import { Menu } from 'lucide-react';
import './Header.css';

export default function Header({ onToggleSidebar, sidebarOpen }) {
  return (
    <header className="app-header">
      {!sidebarOpen && (
        <button className="header-menu-btn" onClick={onToggleSidebar} title="Open sidebar">
          <Menu size={20} />
        </button>
      )}
      <div className="header-title">
        <span className="header-logo">IndicOCR</span>
        <span className="header-subtitle">Indic Language OCR Processing</span>
      </div>
      <div className="header-spacer" />
    </header>
  );
}
