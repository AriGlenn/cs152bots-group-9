import pandas as pd
import vertexai
from vertexai.generative_models import GenerativeModel
import string
import random
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from datasets import load_dataset
import re
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

project_id = "cs152-424619"  # Giancarlo's project ID
vertexai.init(project=project_id, location="us-central1")
model = GenerativeModel(model_name="gemini-1.0-pro-002")

def evaluate_strings_from_csv(csv_file_path):
    df = pd.read_csv(csv_file_path)

    if not {'message', 'label'}.issubset(df.columns):
        raise ValueError("CSV file must contain 'message' and 'label' columns")

    results = []

    for _, row in df.iterrows():
        text = row['message']
        label = row['label']

        auto_report_prompt = (
            "You are reading a message on an online dating platform. You are scanning the message for concerning content. "
            "It is vital that you correctly identify whether or not this message is concerning. Please classify the message "
            "into one of the following categories: 'not concerning content,' 'imminent danger,' 'inauthentic or underage profile,' "
            "'spam or scam,' 'inappropriate or offensive content,' 'trying to move someone onto a different platform,' or 'other concerning content'. "
            "Please be picky about what you flag as concerning content. Assume you are only seeing one isolated message in a long conversation. "
            "If the message is not concerning, please say 'not concerning content'. Provide your answer only as the category name. Do not respond with "
            "anything other than the category name, without any quotes or special characters. Here is the message: "
        )
        full_prompt = auto_report_prompt + text

        auto_report = model.generate_content(full_prompt)
        evaluation_result = ""

        try:
            evaluation_result = auto_report.text
        except ValueError:
            evaluation_result = "vertex safety error"
        
        def extract_category(evaluation_result):
            categories = [
                'not concerning content', 
                'imminent danger', 
                'inauthentic or underage profile', 
                'spam or scam', 
                'inappropriate or offensive content', 
                'trying to move someone onto a different platform', 
                'other concerning content',
                'vertex safety error'
            ]
            
            normalized_result = evaluation_result.strip().lower().strip(string.punctuation).rstrip(string.punctuation)
            for category in categories:
                if category in normalized_result:
                    return category
            return "error"
        
        
        result = extract_category(evaluation_result)
        results.append({'message': text, 'label': label,
                       'predicted_label': result})

    results_df = pd.DataFrame(results)

    results_csv_file_path = 'datasets/vertex_results.csv'
    results_df.to_csv(results_csv_file_path, index=False)
    print(f"Evaluated results saved to {results_csv_file_path}")
    return results_df


def analyze_results(results_df):
    true_labels = results_df['label']
    predicted_labels = results_df['predicted_label']
    print(predicted_labels)
    print(true_labels)

    accuracy_per_category = {}
    for category in results_df['label'].unique():
        category_mask = results_df['label'] == category
        accuracy = accuracy_score(true_labels[category_mask], predicted_labels[category_mask])
        accuracy_per_category[category] = accuracy

    y_labels = list(set(true_labels))
    all_labels = list(set(true_labels))
    all_labels.insert(0, "vertex safety error")
    all_labels.append("error")

    conf_matrix = confusion_matrix(true_labels, predicted_labels, labels=all_labels)
    class_report = classification_report(true_labels, predicted_labels, labels=all_labels, zero_division=1)
   
    print("Accuracy for each category:")
    for category, accuracy in accuracy_per_category.items():
        print(f"{category}: {accuracy}")

    print("\nConfusion Matrix:")
    print(conf_matrix)

    print("\nClassification Report:")
    print(class_report)
    
    conf_matrix = np.delete(conf_matrix, 0, axis=0)
    conf_matrix = np.delete(conf_matrix, -1, axis=0)
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues",
                xticklabels=all_labels, yticklabels=y_labels,
                cbar=False, linewidths=.5, linecolor='black')
               
    plt.xlabel('Predicted Labels')
    plt.ylabel('True Labels')
    plt.title('Confusion Matrix')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig('plots/confusion.png', bbox_inches='tight')

    # 2. Vertex Error 
    vertex_error_counts = (predicted_labels == "vertex safety error").groupby(true_labels).sum()
    label_counts = true_labels.value_counts()
    vertex_error_percentage = (vertex_error_counts / label_counts) * 100

    plt.figure(figsize=(10, 6))
    vertex_error_percentage.plot(kind='bar', color='skyblue')
    plt.xlabel('True Labels')
    plt.ylabel('Percentage of Vertex Safety Error')
    plt.title('Percentage of Times Each Label was Marked as "Vertex Safety Error"')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('plots/vertex_error.png')
    
    # 3. Overall Accuracy
    plt.figure(figsize=(10, 6))
    accuracy_series = pd.Series(accuracy_per_category)
    accuracy_series.plot(kind='bar', color='lightgreen')
    plt.xlabel('Categories')
    plt.ylabel('Accuracy')
    plt.title('Accuracy for Each Category')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('plots/accuracy.png')
    
    # 4. False Positive and False Negative Rates
    non_concerning = 'not concerning content'
    false_positive_rate = 0
    false_negative_rate = 0
    
    false_positives = ((true_labels != non_concerning) & (predicted_labels == non_concerning)).sum()
    false_negatives = ((true_labels == non_concerning) & (predicted_labels != non_concerning)).sum()
    total_non_concerning = (true_labels == non_concerning).sum()
    total_others = (true_labels != non_concerning).sum()

    if total_others > 0:
        false_positive_rate = (false_positives / total_others) * 100
    else:
        false_positive_rate = 0
    
    if total_non_concerning > 0:
        false_negative_rate = (false_negatives / total_non_concerning) * 100
    else:
        false_negative_rate = 0

    rates = pd.DataFrame({
        'Rate': ['False Positive', 'False Negative'],
        'Percentage': [false_positive_rate, false_negative_rate]
    })

    plt.figure(figsize=(10, 6))
    sns.barplot(x='Rate', y='Percentage', data=rates, palette=['red', 'blue'])
    plt.xlabel('Error Type')
    plt.ylabel('Percentage')
    plt.title('False Positive and False Negative Rates')
    plt.tight_layout()
    plt.savefig('plots/false_positive_negative.png')

    
def make_csv(csv_file_path):
    spam_df = pd.read_csv("datasets/spam.csv", nrows = 200)
    danger_df = pd.read_csv("datasets/danger.csv", nrows = 200)
    benign_df = pd.read_csv("datasets/benign.csv", nrows= 200)
    toxic_df = pd.read_csv("datasets/inappropriate.csv", nrows = 200)
    other_df = pd.read_csv("datasets/other.csv", nrows=200)
    platform_df = pd.read_csv("datasets/platform.csv",nrows=200)
    underage_df = pd.read_csv("datasets/inauthentic.csv", nrows=200)

    # Create the categories dictionary
    categories = {
        "spam or scam": spam_df["message"].tolist(),
        "imminent danger": danger_df["message"].tolist(),
        "not concerning content": benign_df["message"].tolist(),
        "inappropriate or offensive content": toxic_df["message"].tolist(),
        "other concerning content": other_df["message"].tolist(),
        "trying to move someone onto a different platform": platform_df["message"].tolist(),
        "inauthentic or underage profile": underage_df["message"].tolist()
    }

    # Prepare the data
    data = []
    for category, phrases in categories.items():
        for phrase in phrases:
            data.append((category, phrase))

    # Convert to DataFrame
    data_df = pd.DataFrame(data, columns=["label", "message"])

    # Shuffle the data
    data_df = data_df.sample(frac=1, random_state=42).reset_index(drop=True)
    df = pd.DataFrame(data_df, columns=['label', 'message'])
    df.to_csv(csv_file_path, index=False)
    print(f"CSV file created at {csv_file_path}")


def main():
    # csv_file_path = 'datasets/eval_data.csv'
    # make_csv(csv_file_path)
    # evaluated_results_df = evaluate_strings_from_csv(csv_file_path)
    # analyze_results(evaluated_results_df)
    results_csv_file_path = 'datasets/vertex_results.csv'
    results_df = pd.read_csv(results_csv_file_path)
    analyze_results(results_df)
  
  
""" Extract spam samples from kaggle dataset """
def process_spam():
    # https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset?select=spam.csv
    df = pd.read_csv('kaggle_spam.csv', encoding='latin1', error_bad_lines=False)
    df = df.dropna(axis=1, how='all')
    spam_df = df[df['label'] == 'spam']
    spam_df['label'] = spam_df['label'].replace('spam', 'spam or scam')
    spam_df.to_csv('datasets/spam.csv', index=False, columns=['label', 'message'])

  
""" Extract innapropriate and not concerning examples from hugging face """
def process_toxic():
    # https://huggingface.co/datasets/lmsys/toxic-chat/viewer/toxicchat0124/train?p=27&f[human_annotation][value]=%27True%27
    dataset = load_dataset("lmsys/toxic-chat", "toxicchat0124")
    df = pd.DataFrame(dataset['train'])

    def preprocess_text(text):
        text = re.sub(r'[{}]'.format(string.punctuation), '', text)  
        text = text.strip() 
        return text

    def count_words(text):
        words = re.findall(r'\w+', text)
        return len(words)

    df['user_input'] = df['user_input'].apply(preprocess_text)

    df_toxic_filtered = df[(df['toxicity'] == True) & 
                        df['user_input'].notnull() &
                        (df['user_input'].apply(lambda x: count_words(x)) < 50)]

    df_toxic_filtered['label'] = "inappropriate or offensive content"
    df_toxic_filtered.rename(columns={'user_input': 'message'}, inplace=True)
    df_toxic_filtered['message'] = df_toxic_filtered['message'].str.replace('\n', ' ').str.replace('\r', ' ')
    df_toxic_filtered[['label', 'message']].to_csv("datasets/inappropriate.csv", index=False, header=True)
    
    print("CSV file saved successfully.")
    
    df_benign_filtered = df[(df['toxicity'] == False) & 
                        df['user_input'].notnull() &
                        (df['user_input'].apply(lambda x: count_words(x)) < 50)]

    df_benign_filtered['label'] = "not concerning content"
    df_benign_filtered.rename(columns={'user_input': 'message'}, inplace=True)
    df_benign_filtered['message'] = df_benign_filtered['message'].str.replace('\n', ' ').str.replace('\r', ' ')
    df_benign_filtered[['label', 'message']].to_csv("datasets/benign.csv", index=False, header=True)

    print("CSV file saved successfully.")


def process_danger():
    # https://kaggle.com/datasets/julian3833/jigsaw-toxic-comment-classification-challenge?select=train.csv
    df = pd.read_csv('datasets/jigsaw.csv', encoding='latin1')
    df_filtered = df[(df['threat'] == True)].copy()
    df_filtered.rename(columns={'comment_text': 'message'}, inplace=True)
    df_filtered.rename(columns={'threat': 'label'}, inplace=True)
    df_filtered['message'] = df_filtered['message'].str.replace('\n', ' ').str.replace('\r', ' ')
    df_filtered['label'].replace(1, 'imminent danger', inplace=True)
    df_filtered.to_csv('datasets/danger.csv', index=False, columns=['label', 'message'])
    print("CSV file saved successfully.")

""" 
GPT prompt (3.5) for other CSV:

Im developing a trust and safety project. I want to find datasets the correspond to the following message categories:

categories = {
    "inauthentic or underage profile": ["I'm 15 years old.", "I'm not who I say I am.", "I'm using a fake ID."],
    "trying to move someone onto a different platform": ["Let's continue this conversation on WhatsApp.", "Add me on Snapchat for more.", "Message me on Instagram."],
    "other concerning content": ["I need help.", "Something doesn't feel right.", "I'm feeling unsafe."]
}

Can you generate 3  different csv, of format: label, message with 100 examples for each?
"""


    
if __name__ == "__main__":
    main()
    