import { useEffect } from 'react';

const SITE_URL = 'https://www.agrobot.in';

const TAGS = [
  ['meta[name="description"]', 'content', 'description'],
  ['link[rel="canonical"]', 'href', 'url'],
  ['meta[property="og:url"]', 'content', 'url'],
  ['meta[property="og:title"]', 'content', 'title'],
  ['meta[property="og:description"]', 'content', 'description'],
  ['meta[name="twitter:title"]', 'content', 'title'],
  ['meta[name="twitter:description"]', 'content', 'description'],
];

/* Sets the per-page title, description and canonical URL, and restores the
   previous values on unmount so pages without their own meta (the logged-in
   app) fall back to the defaults in public/index.html. scripts/prerender.js
   bakes the result into the static HTML that crawlers and link previews read. */
const usePageMeta = ({ title, description, path, noindex = false }) => {
  useEffect(() => {
    const values = { title, description, url: path ? `${SITE_URL}${path}` : null };
    const previousTitle = document.title;
    const restore = [];

    if (title) document.title = title;
    TAGS.forEach(([selector, attr, key]) => {
      const el = document.head.querySelector(selector);
      if (!el || !values[key]) return;
      restore.push([el, attr, el.getAttribute(attr)]);
      el.setAttribute(attr, values[key]);
    });

    let robots = null;
    if (noindex) {
      robots = document.createElement('meta');
      robots.setAttribute('name', 'robots');
      robots.setAttribute('content', 'noindex');
      document.head.appendChild(robots);
    }

    return () => {
      document.title = previousTitle;
      restore.forEach(([el, attr, value]) => el.setAttribute(attr, value));
      if (robots) robots.remove();
    };
  }, [title, description, path, noindex]);
};

export default usePageMeta;
