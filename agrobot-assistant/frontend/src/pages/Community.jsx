import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';
import './FeaturePages.css';

const Community = () => {
  const [posts, setPosts] = useState([]);
  const [form, setForm] = useState({ region: '', crop_tag: '', title: '', body: '' });
  const [replyText, setReplyText] = useState({});

  const load = () => ApiService.getForumPosts().then(setPosts);
  useEffect(() => { load(); }, []);

  const submit = async (event) => {
    event.preventDefault();
    await ApiService.createForumPost(form);
    setForm({ region: '', crop_tag: '', title: '', body: '' });
    load();
  };

  const reply = async (postId) => {
    await ApiService.createForumReply(postId, { body: replyText[postId] || '' });
    setReplyText({ ...replyText, [postId]: '' });
    load();
  };

  return (
    <div className="feature-page"><div className="feature-container">
      <header className="feature-header"><div><h1>Community Forum</h1><p>Ask questions and reply within farming regions.</p></div><Link className="feature-button secondary" to="/dashboard">Dashboard</Link></header>
      <form className="feature-form" onSubmit={submit}>
        <h2>New Post</h2>
        <input value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} placeholder="Region / district" required />
        <input value={form.crop_tag} onChange={(e) => setForm({ ...form, crop_tag: e.target.value })} placeholder="Crop tag" />
        <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Title" required />
        <textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder="Question" required />
        <button className="feature-button">Post</button>
      </form>
      <section className="feature-list">{posts.map((post) => <article className="feature-card" key={post.id}><h3>{post.title}</h3><p>{post.body}</p><p className="feature-muted">{post.region} {post.crop_tag ? `• ${post.crop_tag}` : ''}</p>{post.replies?.map((r) => <p key={r.id}>Reply: {r.body}</p>)}<div className="feature-actions"><input value={replyText[post.id] || ''} onChange={(e) => setReplyText({ ...replyText, [post.id]: e.target.value })} placeholder="Reply" /><button className="feature-button" onClick={() => reply(post.id)}>Reply</button><button className="feature-button secondary" onClick={() => ApiService.reportContent({ target_type: 'post', target_id: post.id, reason: 'Needs review' })}>Report</button></div></article>)}</section>
    </div></div>
  );
};

export default Community;
