import ImageGrid from './ImageGrid'

/**
 * Renders one `/image-grid-blocks/` entry (section_title, anchor_slug,
 * items) as a titled gallery section with its anchor preserved for deep
 * links.
 */
export default function ImageGridBlockSection({ block, columns = 4 }) {
  if (!block) return null
  return (
    <div className="image-grid-block" id={block.anchor_slug || undefined}>
      <div className="section-head">
        {block.section_title && <h3>{block.section_title}</h3>}
        {block.intro && <p className="section-subtitle">{block.intro}</p>}
      </div>
      <ImageGrid items={block.items} columns={columns} />
    </div>
  )
}
