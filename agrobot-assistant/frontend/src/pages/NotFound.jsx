import React from 'react';
import { Link } from 'react-router-dom';
import { Sprout, ArrowRight } from 'lucide-react';
import usePageMeta from '../hooks/usePageMeta';
import './FeaturePages.css';

const ICON = { strokeWidth: 2.75 };

/* A real 404. The old app silently redirected every unknown URL to "/", so a
   stale or mistyped link looked as if the app had forgotten where you were. */
const NotFound = () => {
  usePageMeta({ title: 'Page not found – AgroBot', noindex: true });

  return (
    <div className="notfound">
      <div className="notfound-inner">
        <span className="notfound-mark"><Sprout size={32} {...ICON} /></span>
        <h1>This page isn’t here</h1>
        <p>
          The link may be old, or the page may have moved. Nothing on your farm has changed.
        </p>
        <div className="notfound-actions">
          <Link to="/" className="btn btn-secondary btn-lg">Go to the home page</Link>
          <Link to="/dashboard" className="btn btn-primary btn-lg">
            Open my farm <ArrowRight size={18} {...ICON} />
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
