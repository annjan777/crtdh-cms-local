// Ordered list of a collection's items: select, reorder (drag, or Space then
// arrow keys on the handle), shows hidden items, and adds new ones.
import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Plus } from 'lucide-react';
import { plain } from './validate.js';

export function labelFor(def, values, index) {
  const text = (def.item_label || [])
    .map((n) => values?.[n])
    .filter((x) => x && plain(x).trim())
    .map((x) => plain(x).trim())
    .join(' ');
  const noun = def.item_noun || def.add_label || 'item';
  if (text) return text;
  return `${noun.charAt(0).toUpperCase()}${noun.slice(1)} ${index + 1}`;
}

function Row({ id, label, sublabel, thumb, hidden, selected, onSelect, reorderable, index, total, noun }) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <li ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className={`item-row${selected ? ' is-selected' : ''}${isDragging ? ' is-dragging' : ''}${hidden ? ' is-hidden' : ''}`}>
      {reorderable ? (
        <button
          type="button"
          ref={setActivatorNodeRef}
          className="drag-handle"
          aria-label={`Move ${noun} ${index + 1} of ${total}: ${label}. Press Space, then the arrow keys.`}
          {...attributes}
          {...listeners}
        >
          <GripVertical size={16} aria-hidden="true" />
        </button>
      ) : null}
      <button type="button" className="item-select" aria-current={selected ? 'true' : undefined} onClick={onSelect}>
        {thumb !== undefined ? <span className="thumb">{thumb ? <img src={thumb} alt="" loading="lazy" /> : null}</span> : null}
        <span className="item-text">
          <span className="item-label">{label}</span>
          {sublabel ? <span className="item-sub">{sublabel}</span> : null}
        </span>
        {hidden ? <span className="tag">Hidden</span> : null}
      </button>
    </li>
  );
}

export default function CollectionList({ def, items, records, selectedPk, onSelect, onReorder, onAdd, adding, listLabel }) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const imageField = def.fields.find((f) => f.type === 'image');
  const noun = def.item_noun || def.add_label || 'item';
  const rows = items.map((it, i) => {
    const rec = records[`${def.resource}:${it.pk}`];
    const values = rec?.values || it.values;
    return { id: it.pk, values, index: i };
  });
  const ids = rows.map((r) => r.id);
  const labelOf = (r) => labelFor(def, r.values, r.index);
  const announcements = {
    onDragStart: ({ active }) => `Picked up ${noun} ${ids.indexOf(active.id) + 1}. Use the arrow keys to move it, Space to drop, Escape to cancel.`,
    onDragOver: ({ over }) => (over ? `Moved to position ${ids.indexOf(over.id) + 1} of ${ids.length}.` : ''),
    onDragEnd: ({ over }) => (over ? `Dropped at position ${ids.indexOf(over.id) + 1} of ${ids.length}.` : 'Not moved.'),
    onDragCancel: () => 'Move cancelled. The order is unchanged.',
  };

  function end({ active, over }) {
    if (!over || active.id === over.id) return;
    onReorder(arrayMove(ids, ids.indexOf(active.id), ids.indexOf(over.id)));
  }

  return (
    <div className="collection">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={end} accessibility={{ announcements, screenReaderInstructions: { draggable: 'To move an item, press Space, use the arrow keys, then press Space again.' } }}>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          <ul className="item-list" aria-label={listLabel}>
            {rows.map((r) => (
              <Row
                key={r.id}
                id={r.id}
                index={r.index}
                total={rows.length}
                noun={noun}
                label={labelOf(r)}
                sublabel={def.sublabel ? def.sublabel(r.values) : null}
                thumb={imageField ? r.values[imageField.name] || '' : undefined}
                hidden={r.values.is_published === false}
                selected={r.id === selectedPk}
                reorderable={rows.length > 1}
                onSelect={() => onSelect(r.id)}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>
      <button type="button" className="btn btn-add" onClick={onAdd} aria-busy={adding || undefined}>
        <Plus size={16} aria-hidden="true" />
        Add {noun}
      </button>
    </div>
  );
}
