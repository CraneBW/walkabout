export default function TabBar({ tabs, activeTabId, onSelect, onClose }) {
  if (tabs.length === 0) return null;

  return (
    <div className="tab-bar" role="tablist">
      {tabs.map((tab) => {
        const classes = ['tab-bar-item'];
        if (tab.id === activeTabId) classes.push('tab-bar-item-active');
        if (tab.dirty) classes.push('tab-bar-item-dirty');

        return (
          <div
            key={tab.id}
            className={classes.join(' ')}
            onClick={() => onSelect(tab.id)}
            role="tab"
            aria-selected={tab.id === activeTabId}
          >
            <span className="tab-label">{tab.path.split('/').pop()}</span>
            {tab.dirty && <span className="dirty-indicator">*</span>}
            {tabs.length > 1 && (
              <button
                className="close-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onClose(tab.id);
                }}
              >
                &times;
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
