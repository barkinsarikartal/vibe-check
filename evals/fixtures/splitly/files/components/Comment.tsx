type Props = { author: string; body: string; createdAt: string }

export default function Comment({ author, body, createdAt }: Props) {
  return (
    <div className="comment">
      <strong>{author}</strong> <span className="muted">{new Date(createdAt).toLocaleString()}</span>
      {/* comments support basic formatting like <b> and links */}
      <p dangerouslySetInnerHTML={{ __html: body }} />
    </div>
  )
}
