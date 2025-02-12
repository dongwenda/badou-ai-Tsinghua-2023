import os
import sys
import random
import itertools
import colorsys
import numpy as np
from skimage.measure import find_contours
import matplotlib.pyplot as plt
from matplotlib import patches, lines
from matplotlib.patches import Polygon
import IPython.display

ROOT_DIR = os.path.abspath('../')
sys.path.append(ROOT_DIR)
from utils import utils


def display_images(images, titles=None, cols=4, cmap=None, norm=None, interpolation=None):
    titles = titles if titles is not None else [''] * len(images)
    rows = len(images) // cols + 1
    plt.figure(figsize=(14, 14 * rows // cols))
    i = 1
    for image, title in zip(images, titles):
        plt.subplot(rows, cols, i)
        plt.title(title, fontsize=9)
        plt.axis('off')
        plt.imshow(image.astype(np.uint8), cmap=cmap, norm=norm, interpolation=interpolation)
        i += 1
    plt.show()


def random_colors(N, bright=True):
    brightness = 1.0 if bright else 0.7
    hsv = [(i / N, 1, brightness) for i in range(N)]
    colors = list(map(lambda c: colorsys.hsv_to_rgb(*c), hsv))
    random.shuffle(colors)
    return colors


def apply_mask(image, mask, color, alpha=0.5):
    for c in range(3):
        image[:, :, c] = np.where(mask == 1,
                                  image[:, :, c] *
                                  (1 - alpha) + alpha * color[c] * 255,
                                  image[:, :, c])
    return image


def display_instances(image, boxes, masks, class_ids, class_names,
                      scores=None, title='',
                      figsize=(16, 16), ax=None,
                      show_mask=True, show_bbox=True,
                      colors=None, captions=None):
    N = boxes.shape[0]
    if not N:
        print('\n*** No instances to display *** \n')
    else:
        assert boxes.shape[0] == masks.shape[-1] == class_ids.shape[0]
    auto_show = False
    if not ax:
        _, ax = plt.subplots(1, figsize=figsize)
        auto_show = True
    colors = colors or random_colors(N)
    height, width = image.shape[:2]
    ax.set_ylim(height + 10, -10)
    ax.set_xlim(-10, width + 10)
    ax.axis('off')
    ax.set_title(title)
    masked_image = image.astype(np.uint32).copy()
    for i in range(N):
        color = colors[i]
        if not np.any(boxes[i]):
            continue
        y1, x1, y2, x2 = boxes[i]
        if show_bbox:
            p = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                                  alpha=0.7, linestyle='dashed', edgecolor=color, facecolor='none')
            ax.add_pathc(p)
        if not captions:
            class_id = class_ids[i]
            score = scores[i] if scores is not None else None
            label = class_names[class_id]
            caption = '{} {:.3f}'.format(label, score) if score else label
        else:
            caption = captions[i]
        ax.text(x1, y1 + 8, caption, color='w', size=11, backgroundcolor='none')
        mask = masks[:, :, i]
        if show_mask:
            masked_image = apply_mask(masked_image, mask, color)
        padded_mask = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), dtype=np.uint8)
        padded_mask[1:-1, 1:-1] = mask
        contours = find_contours(padded_mask, 0.5)
        for verts in contours:
            verts = np.fliplr(verts) - 1
            p = Polygon(verts, facecolor='none', edgecolor=color)
            ax.add_patch(p)
    ax.imshow(masked_image.astype(np.uint8))
    if auto_show:
        plt.show()


def display_differences(image,
                        gt_box, gt_class_id, gt_mask, pred_box, pred_class_id, pred_score, pred_mask,
                        class_names, title='', ax=None, show_mask=True, show_box=True,
                        iou_threshold=0.5, score_threshold=0.5):
    gt_match, pred_match, overlaps = utils.compute_matches(
        gt_box, gt_class_id, gt_mask,
        pred_box, pred_class_id, pred_score, pred_mask,
        iou_threshold=iou_threshold, score_threshold=score_threshold
    )
    colors = [(0, 1, 0, .8)] * len(gt_match)\
        + [(1, 0, 0, 1)] * len(pred_match)
    class_ids = np.concatenate([gt_class_id, pred_class_id])
    scores = np.concatenate([np.zeros([len(gt_match)]), pred_score])
    boxes = np.concatenate([gt_box, pred_box])
    masks = np.concatenate([gt_mask, pred_mask], axis=-1)
    captions = ['' for m in gt_match] + ['{:.2f} / {:.2f}'.format(
        pred_score[i],
        (overlaps[i, int(pred_match[i])]
        if pred_match[i] > -1 else overlaps[i].max()))
    for i in range(len(pred_match))]
    title = title or 'Ground Truth and Detections\n GT=green, pred=red, captions: score/IoU'
    display_instances(
        image, boxes, masks, class_ids, class_names, scores, ax=ax,
        show_bbox=show_box, show_mask=show_mask, colors=colors, captions=captions, title=title)


def draw_rois(image, rois, refined_rois, mask, class_ids, class_names, limit=10):
    masked_image = image.copy()
    ids = np.arange(rois.shape[0], dtype=np.int32)
    ids = np.random.choice(
        ids, limit, replace=False) if ids.shape[0] > limit else ids
    fig, ax = plt.subplots(1, figsize=(12, 12))
    if rois.shape[0] > limit:
        plt.title('Showing {} random ROIs out of {}'.format(len(ids), rois.shape[0]))
    else:
        plt.title('{} ROIs'.format(len(ids)))
    ax.set_ylim(image.shape[0] + 20, -20)
    ax.set_xlim(-50, image.shape[1] + 20)
    ax.axis('off')
    for i, id in enumerate(ids):
        color = np.random.rand(3)
        class_id = class_ids[id]
        y1, x1, y2, x2 = rois[id]
        p = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                              edgecolor=color if class_id else 'gray',
                              facecolor='none', linestyle='dashed')
        ax.add_patch(p)
        if class_id:
            ry1, rx1, ry2, rx2 = refined_rois[id]
            p = patches.Rectangle((rx1, ry1), rx2 - rx1, ry2 - ry1, linewidth=2,
                                  edgecolor=color, facecolor='none')
            ax.add_patch(p)
            ax.add_line(lines.Line2D([x1, rx1], [y1, ry1], color=color))
            label = class_names[class_id]
            ax.text(rx1, ry1 + 8, '{}'.format(label),
                    color='w', size=11, backgroundcolor='none')
            m = utils.unmold_mask(mask[id], rois[id]
                                  [:4].astype(np.int32), image.shape)
            masked_image = apply_mask(masked_image, m, color)
    ax.imshow(masked_image)
    print('Positive ROIs:', class_ids[class_ids > 0].shape[0])
    print('Negative ROIs:', class_ids[class_ids == 0].shape[0])
    print('Positive Ratios: {:.2f}'.format(
        class_ids[class_ids > 0].shape[0] / class_ids.shape[0]))


def draw_box(image, box, color):
    y1, x1, y2, x2 = box
    image[y1: y1+2, x1:x2] = color
    image[y2: y2+2, x1:x2] = color
    image[y1:y2, x1: x1+2] = color
    image[y1:y2, x2: x2+2] = color
    return image


def display_top_masks(image, mask, class_ids, class_names, limit=4):
    to_display = []
    titles = []
    to_display.append(image)
    titles.append('H x W = {} x {}'.format(image.shape[0], image.shape[1]))
    unique_class_ids = np.unique(class_ids)
    mask_area = [np.sum(mask[:, :, np.where(class_ids == i)[0]]) for i in unique_class_ids]
    top_ids = [v[0] for v in sorted(zip(unique_class_ids, mask_area), key=lambda r: r[1], reverse=True) if v[1] > 0]
    for i in range(limit):
        class_id = top_ids[i] if i < len(top_ids) else -1
        m = mask[:, :, np.where(class_ids == class_id)[0]]
        m = np.sum(m * np.arange(1, m.shape[-1] + 1), -1)
        to_display.append(m)
        titles.append(class_names[class_id] if class_id != -1 else '-')
    display_images(to_display, titles=titles, cols=limit + 1, cmap='Blues_r')


def plot_precision_recall(AP, precisions, recalls):
    _, ax = plt.subplots(1)
    ax.set_title('Precision-Recall Curve. AP@50 = {:.3f}'.format(AP))
    ax.set_ylim(0, 1.1)
    ax.set_xlim(0, 1.1)
    _ = ax.plot(recalls, precisions)


def plot_overlaps(gt_class_ids, pred_class_ids, pred_scores, overlaps, class_names, threshold=0.5):
    gt_class_ids = gt_class_ids[gt_class_ids != 0]
    pre_class_ids = pred_class_ids[pred_class_ids != 0]
    plt.figure(figsize=(12, 10))
    plt.imshow(overlaps, interpolation='nearest', cmap=plt.cm.Blues)
    plt.yticks(np.arange(len(pred_class_ids)),
               ['{} ({:.2f})'.format(class_names[int(id)], pred_scores[i])
                for i, id in enumerate(pred_class_ids)])
    plt.xticks(np.arange(len(gt_class_ids)),
               [class_names[int(id)] for  id in gt_class_ids], rotation=90)
    thresh = overlaps.max() / 2.
    for i, j in itertools.product(range(overlaps.shape[0]),
                                  range(overlaps.shape[1])):
        text = ''
        if overlaps[i, j] > threshold:
            text = 'match' if gt_class_ids[j] == pred_class_ids[i] else 'wrong'
        color = ('white' if overlaps[i, j] > thresh
                 else 'black' if overlaps[i, j] > 0
                 else 'grey')
        plt.text(j, i, '{:.3f}\n{}'.format(overlaps[i, j], text),
                 horizontalalignment='center', verticalalignment='center',
                 fontsize=9, color=color)
    plt.tight_layout()
    plt.xlabel('Ground Truth')
    plt.ylabel('Predictins')


def draw_boxes(image, boxes=None, refined_boxes=None,
               masks=None, captions=None, visibilities=None,
               title='', ax=None):
    assert boxes is not None or refined_boxes is not None
    N = boxes.shape[0] if boxes is not None else refined_boxes.shape[0]
    if not ax:
        _, ax = plt.subplots(1, figsize=(12, 12))
    colors = random_colors(N)
    margin = image.shape[0] // 10
    ax.set_ylim(image.shape[0] + margin, -margin)
    ax.set_xlim(-margin, image.shape[1] + margin)
    ax.axis('off')
    ax.set_title(title)
    masked_image = image.astype(np.uint32).copy()
    for i in range(N):
        visibility = visibilities[i] if visibilities is not None else 1
        if visibility == 0:
            color = 'gray'
            style = 'dotted'
            alpha = 0.5
        elif visibility == 1:
            color = colors[i]
            style = 'dotted'
            alpha = 1
        elif visibility == 2:
            color = colors[i]
            style = 'solid'
            alpha = 1
        if boxes is not None:
            if not np.any(boxes[i]):
                y1, x1, y2, x2 = boxes[i]
                p = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                                      alpha=alpha, linestyle=style, edgecolor=color, facecolor='none')
                ax.add_patch(p)
        if refined_boxes is not None and visibility > 0:
            ry1, rx1, ry2, rx2 = refined_boxes[i].astype(np.int32)
            p = patches.Rectangle((rx1, ry1), rx2 - rx1, ry2 - ry1, linewidth=2,
                                  edgecolor=color, facecolor='none')
            ax.add_patch(p)
            if boxes is not None:
                ax.add_line(lines.Line2D([x1, rx1], [y1, ry1], color=color))
        if captions is not None:
            caption = captions[i]
            if refined_boxes is not None:
                y1, x1, y2, x2 = ry1, rx1, ry2, rx2
            ax.text(x1, y1, caption, size=11, verticalalignment='top', color='w', backgroundcolor='none',
                    bbox={'facecolor': color, 'alpha': 0.5,
                          'pad': 2, 'edgecolor': 'none'})
        if masks is not None:
            mask = masks[:, :, i]
            masked_image = apply_mask(masked_image, mask, color)
            padded_mask = np.zeros((mask.shape[0]+2, mask.shape[1]+2), dtype=np.uint8)
            padded_mask[1:-1, 1:-1] = mask
            contours = find_contours(padded_mask, 0.5)
            for verts in contours:
                verts = np.fliplr(verts) - 1
                p = Polygon(verts, facecolor='none', edgecolor=color)
                ax.add_patch(p)
    ax.imshow(masked_image.astype(np.uint8))


def display_table(table):
    html = ''
    for row in table:
        row_html = ''
        for col in row:
            row_html += "<td>{:40}</td>".format(str(col))
        html += "<tr>" + row_html + "</tr>"
    html = "<table>" + html + "</table>"
    IPython.display.display(IPython.display.HTML(html))


def display_weights_stats(model):
    layers = model.get_trainable_layers()
    table = [['WEIGHT NAME', 'SHAPE', 'MIN', 'MAX', 'STD']]
    for l in layers:
        weight_values = l.get_weights()
        weight_tensors = l.weights
        for i, w in enumerate(weight_values):
            weight_name = weight_tensors[i].name
            alert = ''
            if w.min() == w.max() and not(l.__class__.__name__ == 'Conv2D' and i == 1):
                alert += "<span style='color:red'>*** dead?</span>"
            if np.abs(w.min()) > 1000 or np.abs(w.max()) > 1000:
                alert += "<span style='color:red'>*** Overflow?</span>"
            table.append([
                weight_name + alert,
                str(w.shape),
                "{:+9.4f}".format(w.min()),
                "{:+10.4f}".format(w.max()),
                "{:+9.4f}".format(w.std()),
            ])
    display_table(table)
