import argparse
import textattack
import torch
import sys

from attack_args_helper import get_args, parse_model_from_args, parse_dataset_from_args

def _cb(s): return textattack.shared.utils.color_text(str(s), color='blue', method='stdout')
def _cg(s): return textattack.shared.utils.color_text(str(s), color='green', method='stdout')
def _cr(s): return textattack.shared.utils.color_text(str(s), color='red', method='stdout')
def _pb(): print(_cg('-' * 60))

from collections import Counter

def get_num_successes(model, ids, true_labels):
    ids = textattack.shared.utils.preprocess_ids(ids)
    id_dim = torch.tensor(ids).ndim
    if id_dim == 2:
        # For models where the input is a single vector.
        ids = torch.tensor(ids).to(textattack.shared.utils.device)
        preds = model(ids)
    elif id_dim == 3:
        # For models that take multiple vectors per input.
        ids = map(torch.tensor, zip(*ids))
        ids = (x.to(textattack.shared.utils.device) for x in ids)
        preds = model(*ids)
    else:
        raise TypeError(f'Error: malformed id_dim ({id_dim})')
    true_labels = torch.tensor(true_labels).to(textattack.shared.utils.device)
    if isinstance(preds, tuple):
        preds = preds[0]
    guess_labels = preds.argmax(dim=1)
    successes = (guess_labels == true_labels).sum().item()
    return successes, true_labels, guess_labels

def test_model_on_dataset(model, dataset, batch_size=16, num_examples=1000):
    succ = 0
    fail = 0
    batch_ids = []
    batch_labels = []
    all_true_labels = []
    all_guess_labels = []
    for i, (text, label) in enumerate(dataset):
        if i >= num_examples: break
        ids = model.tokenizer.encode(text)
        batch_ids.append(ids)
        batch_labels.append(label)
        if len(batch_ids) == batch_size:
            batch_succ, true_labels, guess_labels = get_num_successes(model, batch_ids, batch_labels)
            batch_fail = batch_size - batch_succ
            succ += batch_succ
            fail += batch_fail
            batch_ids = []
            batch_labels = []
            all_true_labels.extend(true_labels.tolist())
            all_guess_labels.extend(guess_labels.tolist())
    if len(batch_ids) > 0:
        batch_succ, true_labels, guess_labels = get_num_successes(model, batch_ids, batch_labels)
        batch_fail = len(batch_ids) - batch_succ
        succ += batch_succ
        fail += batch_fail
        all_true_labels.extend(true_labels.tolist())
        all_guess_labels.extend(guess_labels.tolist())
    
    perc = float(succ)/(succ+fail)*100.0
    perc = '{:.2f}%'.format(perc)
    print(f'Successes {succ}/{succ+fail} ({_cb(perc)})')
    return perc

if __name__ == '__main__': 
    args = get_args()
    
    model = parse_model_from_args(args)
    dataset = parse_dataset_from_args(args)
    
    with torch.no_grad():
        test_model_on_dataset(model, dataset, num_examples=args.num_examples)