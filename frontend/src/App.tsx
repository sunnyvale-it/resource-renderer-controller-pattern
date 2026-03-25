import { useState, useEffect } from 'react'

// API base URL injected or defaults to localhost
const API_BASE = (window as any).API_BASE_URL || 'http://localhost:8000';

interface AppConfig {
  id: number;
  name: string;
  repository_url: string;
  branch: string;
  environment: string;
}

function App() {
  const [configs, setConfigs] = useState<AppConfig[]>([]);
  const [formData, setFormData] = useState({ name: '', repository_url: '', branch: 'main', environment: 'production' });
  const [editingId, setEditingId] = useState<number | null>(null);

  const fetchConfigs = async () => {
    try {
      const res = await fetch(`${API_BASE}/appconfigs/`);
      const data = await res.json();
      setConfigs(data || []);
    } catch (e) {
      console.error("Error fetching configs:", e);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleEdit = (config: AppConfig) => {
    setFormData({
      name: config.name,
      repository_url: config.repository_url,
      branch: config.branch,
      environment: config.environment
    });
    setEditingId(config.id);
  };

  const handleCancelEdit = () => {
    setFormData({ name: '', repository_url: '', branch: 'main', environment: 'production' });
    setEditingId(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await fetch(`${API_BASE}/appconfigs/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        setEditingId(null);
      } else {
        await fetch(`${API_BASE}/appconfigs/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      setFormData({ name: '', repository_url: '', branch: 'main', environment: 'production' });
      fetchConfigs();
    } catch (e) {
      console.error("Failed to save config", e);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`${API_BASE}/appconfigs/${id}`, { method: 'DELETE' });
      fetchConfigs();
    } catch (e) {
      console.error("Failed to delete config", e);
    }
  };

  return (
    <div className="app-container">
      <h1>Resource Renderer Controller</h1>
      
      <form onSubmit={handleSubmit} style={{ marginBottom: '40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
          <div className="form-group">
            <label>Name</label>
            <input name="name" value={formData.name} onChange={handleInputChange} required placeholder="e.g. backend-api" disabled={!!editingId} />
          </div>
          <div className="form-group">
            <label>Environment</label>
            <input name="environment" value={formData.environment} onChange={handleInputChange} required placeholder="e.g. production" />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Repository URL</label>
            <input name="repository_url" value={formData.repository_url} onChange={handleInputChange} required placeholder="https://github.com/org/repo.git" />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Branch</label>
            <input name="branch" value={formData.branch} onChange={handleInputChange} required placeholder="main" />
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
          <button type="submit" style={{ flex: 1 }}>{editingId ? 'Update Config' : 'Create Config'}</button>
          {editingId && (
            <button type="button" onClick={handleCancelEdit} style={{ flex: 1, backgroundColor: '#475569' }}>Cancel</button>
          )}
        </div>
      </form>

      <div className="configs-list">
        {configs.length > 0 ? configs.map(config => (
          <div key={config.id} className="item-card">
            <div className="item-details" style={{ flex: 1 }}>
              <h3>{config.name} <span style={{fontSize: '0.8em', color: '#38bdf8'}}>[{config.environment}]</span></h3>
              <p>Repo: {config.repository_url}</p>
              <p>Branch: {config.branch}</p>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexDirection: 'column' }}>
              <button 
                type="button" 
                onClick={() => handleEdit(config)} 
                style={{ backgroundColor: '#f59e0b', padding: '0.4rem 0.8rem', fontSize: '0.8em' }}
              >
                Edit
              </button>
              <button 
                className="danger" 
                onClick={() => handleDelete(config.id)}
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8em' }}
              >
                Delete
              </button>
            </div>
          </div>
        )) : <p style={{textAlign: 'center', color: '#94a3b8'}}>No configurations found. Create one above.</p>}
      </div>
    </div>
  )
}

export default App
