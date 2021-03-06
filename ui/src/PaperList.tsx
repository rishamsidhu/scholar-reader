import React from "react";
import PaperSummary from "./PaperSummary";
import { PaperId, Papers, UserLibrary } from "./state";

interface Props {
  paperId?: PaperId;
  papers: Papers | null;
  userLibrary: UserLibrary | null;
  handleAddPaperToLibrary: (paperId: string, paperTitle: string) => void;
}

export class PaperList extends React.PureComponent<Props> {
  render() {
    const { papers } = this.props;
    return papers !== null ? (
      <div className="paper-list">
        {Object.keys(papers).map((paperId) => (
          <PaperSummary
            key={paperId}
            openedPaperId={this.props.paperId}
            paper={papers[paperId]}
            userLibrary={this.props.userLibrary}
            handleAddPaperToLibrary={this.props.handleAddPaperToLibrary}
          />
        ))}
      </div>
    ) : (
      <p>Information for cited papers is not yet loaded.</p>
    );
  }
}

export default PaperList;
