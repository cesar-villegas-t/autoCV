import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { GenerationForm } from './features/generation/GenerationForm';
import './style.css';

createRoot(document.getElementById('root')!).render(<StrictMode><GenerationForm /></StrictMode>);
